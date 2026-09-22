# -*- coding: utf-8 -*-
import os
import odoo
from odoo import api

def run_test():
    odoo.tools.config['db_name'] = 'facturation_electronique'
    odoo.tools.config['db_host'] = 'db'
    odoo.tools.config['db_user'] = 'odoo'
    odoo.tools.config['db_password'] = 'odoo'

    registry = odoo.registry('facturation_electronique')
    with registry.cursor() as cr:
        env = api.Environment(cr, odoo.SUPERUSER_ID, {})

        print("\n=======================================================")
        print("TEST: NOUVEAU MODÈLE FACTURE HONORAIRES / CONSULTANT")
        print("=======================================================")

        # 1. Vérification du modèle de facture dans la galerie
        modele = env['btp.facture.modele'].search([('code', '=', 'honoraires_consultant')], limit=1)
        assert modele, "Le modèle 'honoraires_consultant' doit exister dans la galerie btp.facture.modele !"
        assert modele.image_preview, "Le modèle 'honoraires_consultant' doit avoir son image de prévisualisation !"
        print(f"-> Modèle trouvé: '{modele.name}' (Code: {modele.code}) | Image: {len(modele.image_preview)} octets")

        # 2. Création d'une facture client avec ce modèle
        partner = env['res.partner'].search([('customer_rank', '>', 0)], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': 'Société d’Ingénierie et d’Études Africaines'})

        move = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': modele.id,
            'honoraire_city': 'Ouagadougou',
            'honoraire_objet': "Mission d'audit, d'évaluation technique et de suivi architectural du projet",
            'honoraire_signataire_titre': "Signataire",
            'honoraire_signataire_nom': "Dr. KABORE Ousmane",
            'honoraire_unite': "Mission",
            'honoraire_quantite': 1.0,
            'honoraire_montant': 10000000.0,
            'honoraire_frais_remboursables': 2000000.0,
        })

        # Forcer le calcul des 10 lignes
        move._compute_honoraire_lines()

        print("\n--- VÉRIFICATION MATHÉMATIQUE DES 10 LIGNES (VALEURS DE TEST: 10M & 2M) ---")
        print(f"Ligne 1 (Honoraires): {move.honoraire_line_1_montant:,.0f} FCFA")
        print(f"Ligne 2 (Frais Remboursables): {move.honoraire_line_2_montant:,.0f} FCFA")
        print(f"Ligne 3 (Total Prestation): {move.honoraire_line_3_total_prestation:,.0f} FCFA")
        print(f"Ligne 4 (Paiement 1ère Tranche 30% Honoraires): {move.honoraire_line_4_tranche_1_honoraire:,.0f} FCFA")
        print(f"Ligne 5 (Paiement 1ère Tranche 100% Frais): {move.honoraire_line_5_tranche_1_frais:,.0f} FCFA")
        print(f"Ligne 6 (Total Règlement 1ère Tranche): {move.honoraire_line_6_total_tranche_1:,.0f} FCFA")
        print(f"Ligne 7 (Paiement 2ème Tranche 30% Honoraires): {move.honoraire_line_7_tranche_2_honoraire:,.0f} FCFA")
        print(f"Ligne 8 (Paiement 3ème Tranche 40% Honoraires): {move.honoraire_line_8_tranche_3_honoraire:,.0f} FCFA")
        print(f"Ligne 9 (Retenue à la source 5%): {move.honoraire_line_9_retenue_source:,.0f} FCFA")
        print(f"Ligne 10 (Net à payer Tranche 2+3): {move.honoraire_line_10_net_a_payer:,.0f} FCFA")
        print(f"Arrêtée en lettres: {move.honoraire_net_lettres}")

        # Assertions strictes
        assert move.honoraire_line_1_montant == 10000000.0, "Ligne 1 incorrecte !"
        assert move.honoraire_line_2_montant == 2000000.0, "Ligne 2 incorrecte !"
        assert move.honoraire_line_3_total_prestation == 12000000.0, "Ligne 3 incorrecte !"
        assert move.honoraire_line_4_tranche_1_honoraire == 3000000.0, "Ligne 4 incorrecte !"
        assert move.honoraire_line_5_tranche_1_frais == 2000000.0, "Ligne 5 incorrecte !"
        assert move.honoraire_line_6_total_tranche_1 == 5000000.0, "Ligne 6 incorrecte !"
        assert move.honoraire_line_7_tranche_2_honoraire == 3000000.0, "Ligne 7 incorrecte !"
        assert move.honoraire_line_8_tranche_3_honoraire == 4000000.0, "Ligne 8 incorrecte !"
        assert move.honoraire_line_9_retenue_source == 600000.0, "Ligne 9 incorrecte !"
        assert move.honoraire_line_10_net_a_payer == 6400000.0, "Ligne 10 incorrecte !"

        # Contrôle d'équilibre financier
        total_reconstitue = (
            move.honoraire_line_6_total_tranche_1 +
            move.honoraire_line_10_net_a_payer +
            move.honoraire_line_9_retenue_source
        )
        assert total_reconstitue == move.honoraire_line_3_total_prestation, "Incohérence dans l'équilibre financier global !"
        print(f"-> Contrôle d'équilibre parfait: Tranche 1 (5M) + Net 2+3 (6.4M) + Retenue 5% (600K) = Total Prestation (12M) : EXACT !")

        # 3. Test de validation de la facture (action_post)
        print("\n--- VALIDATION COMPTABLE DE LA FACTURE ---")
        move.action_post()
        assert move.state == 'posted', "La facture doit pouvoir être validée comptablement !"
        print(f"-> Facture validée avec succès: Statut = {move.state}, Numéro = {move.name}")

        # 4. Test d'impression du rapport PDF officiel
        print("\n--- GÉNÉRATION DU RAPPORT PDF OFFICIEL ---")
        pdf_content, _ = env['ir.actions.report']._render_qweb_pdf(
            'btp_decompte.action_report_facture_honoraires',
            [move.id]
        )
        assert pdf_content and len(pdf_content) > 5000, f"Le PDF doit être généré et non vide ({len(pdf_content)} octets)"
        pdf_path = os.path.join(os.path.dirname(__file__), '..', 'facture_honoraires_test.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        print(f"-> PDF officiel généré avec succès ({len(pdf_content):,} octets) : {pdf_path}")

        # 5. Vérification de non-régression sur les autres modèles
        print("\n--- CONTRÔLE DE NON-RÉGRESSION SUR LES FACTURES EXISTANTES ---")
        modele_bordereau = env['btp.facture.modele'].search([('code', '=', 'bordereau_travaux')], limit=1)
        assert modele_bordereau, "Le modèle bordereau doit toujours exister !"
        move_b = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': modele_bordereau.id,
            'facture_amount_presente_ht': 1000000.0,
            'facture_marche_ht': 1000000.0,
        })
        move_b._compute_facture_bordereau_totals()
        assert move_b.facture_net_ttc == 590000.0, f"Le calcul bordereau a été altéré: {move_b.facture_net_ttc} != 590000"
        print(f"-> Modèle Bordereau de travaux: 100% Fonctionnel (Net TTC: {move_b.facture_net_ttc:,.0f} FCFA)")

        cr.rollback()
        print("\n=======================================================")
        print("TOUS LES TESTS DU MODÈLE HONORAIRES ONT RÉUSSI AVEC SUCCÈS !")
        print("=======================================================\n")

if __name__ == '__main__':
    run_test()
