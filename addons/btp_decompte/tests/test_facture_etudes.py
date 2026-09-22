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
        print("TEST: NOUVEAU MODÈLE FACTURE BTP — HONORAIRES / ÉTUDES")
        print("=======================================================")

        # 1. Vérification du modèle dans la galerie
        modele = env['btp.facture.modele'].search([('code', '=', 'honoraires_etudes')], limit=1)
        assert modele, "Le modèle 'honoraires_etudes' doit exister dans btp.facture.modele !"
        assert modele.image_preview, "Le modèle 'honoraires_etudes' doit avoir son image de prévisualisation !"
        print(f"-> Modèle trouvé: '{modele.name}' (Code: {modele.code}) | Image: {len(modele.image_preview)} octets")

        # 2. Création d'une facture client avec ce modèle
        partner = env['res.partner'].search([('customer_rank', '>', 0)], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': 'Direction Générale des Pistes Rurales'})

        move = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': modele.id,
            'etude_city': 'Ouagadougou',
            'etude_marche_num': 'N° 2026-045/MID/SG/DGI',
            'etude_marche_montant': 15000000.0,
            'etude_financement': 'Budget de l’État (Exercice 2026)',
            'etude_objet': "ÉTUDES TECHNIQUES ET CONTRÔLE DES TRAVAUX D'AMÉNAGEMENT DE LA ROUTE INTER-ÉTATS",
            'etude_signataire_titre': 'Le Bureau',
            'etude_signataire_nom': 'BUREAU D’ÉTUDES GÉOCONSEIL',
            'etude_tva_rate': 18.0,
        })

        # Initialiser les 10 lignes types du modèle
        move.action_init_default_etude_lines()
        assert len(move.etude_line_ids) == 10, f"Il doit y avoir exactement 10 lignes types (obtenu: {len(move.etude_line_ids)})"

        # Renseigner des valeurs de test correspondant exactement à l'exemple du prompt
        # SECTION I : HONORAIRES (Total = 6 000 000 FCFA)
        l1 = move.etude_line_ids.filtered(lambda l: l.line_number == 'I.1')
        l1.write({'quantity': 2.0, 'price_unit': 1500000.0}) # 3 000 000

        l2 = move.etude_line_ids.filtered(lambda l: l.line_number == 'I.2')
        l2.write({'quantity': 2.0, 'price_unit': 1000000.0}) # 2 000 000

        l3 = move.etude_line_ids.filtered(lambda l: l.line_number == 'I.3')
        l3.write({'quantity': 1.0, 'price_unit': 1000000.0}) # 1 000 000

        # SECTION II : FRAIS REMBOURSABLE (Total = 2 000 000 FCFA)
        l4 = move.etude_line_ids.filtered(lambda l: l.line_number == 'II.1')
        l4.write({'quantity': 1.0, 'price_unit': 500000.0})  # 500 000

        l5 = move.etude_line_ids.filtered(lambda l: l.line_number == 'II.2')
        l5.write({'quantity': 1.0, 'price_unit': 1500000.0}) # 1 500 000

        # SECTION III : FRAIS DIVERS (Total = 2 000 000 FCFA)
        l6 = move.etude_line_ids.filtered(lambda l: l.line_number == 'III.1')
        l6.write({'quantity': 2.0, 'price_unit': 500000.0})  # 1 000 000

        l7 = move.etude_line_ids.filtered(lambda l: l.line_number == 'III.2')
        l7.write({'quantity': 1.0, 'price_unit': 300000.0})  # 300 000

        l8 = move.etude_line_ids.filtered(lambda l: l.line_number == 'III.3')
        l8.write({'quantity': 1.0, 'price_unit': 400000.0})  # 400 000

        l9 = move.etude_line_ids.filtered(lambda l: l.line_number == 'III.4')
        l9.write({'quantity': 1.0, 'price_unit': 200000.0})  # 200 000

        l10 = move.etude_line_ids.filtered(lambda l: l.line_number == 'III.5')
        l10.write({'quantity': 1.0, 'price_unit': 100000.0}) # 100 000

        # Forcer le recalcul des totaux
        move._compute_etude_totals()

        print("\n--- VÉRIFICATION DES CALCULS DES SECTIONS & TOTAUX ---")
        print(f"Sous-Total I (Honoraires): {move.etude_sous_total_1:,.0f} FCFA")
        print(f"Sous-Total II (Frais Remboursable): {move.etude_sous_total_2:,.0f} FCFA")
        print(f"Sous-Total III (Frais Divers): {move.etude_sous_total_3:,.0f} FCFA")
        print(f"TOTAL GENERAL HTVA: {move.etude_total_htva:,.0f} FCFA")
        print(f"TVA 18%: {move.etude_total_tva:,.0f} FCFA")
        print(f"MONTANT NET A PAYER: {move.etude_net_a_payer:,.0f} FCFA")
        print(f"Arrêtée en lettres: {move.etude_net_lettres}")

        # Assertions strictes
        assert move.etude_sous_total_1 == 6000000.0, f"Sous-total I incorrect: {move.etude_sous_total_1}"
        assert move.etude_sous_total_2 == 2000000.0, f"Sous-total II incorrect: {move.etude_sous_total_2}"
        assert move.etude_sous_total_3 == 2000000.0, f"Sous-total III incorrect: {move.etude_sous_total_3}"
        assert move.etude_total_htva == 10000000.0, f"Total Général HTVA incorrect: {move.etude_total_htva}"
        assert move.etude_total_tva == 1800000.0, f"TVA 18% incorrecte: {move.etude_total_tva}"
        assert move.etude_net_a_payer == 11800000.0, f"Net à payer incorrect: {move.etude_net_a_payer}"
        print("-> Vérification mathématique exacte: 10M HTVA + 1.8M TVA = 11.8M Net à Payer : PARFAIT !")

        # 3. Test de validation comptable (action_post)
        print("\n--- VALIDATION COMPTABLE DE LA FACTURE ---")
        move.action_post()
        assert move.state == 'posted', "La facture doit pouvoir être validée comptablement !"
        print(f"-> Facture validée avec succès: Statut = {move.state}, Numéro = {move.name}")

        # 4. Test d'impression du rapport PDF officiel
        print("\n--- GÉNÉRATION DU RAPPORT PDF OFFICIEL ---")
        pdf_content, _ = env['ir.actions.report']._render_qweb_pdf(
            'btp_decompte.action_report_facture_etudes',
            [move.id]
        )
        assert pdf_content and len(pdf_content) > 5000, f"Le PDF doit être généré et non vide ({len(pdf_content)} octets)"
        pdf_path = os.path.join(os.path.dirname(__file__), '..', 'facture_etudes_test.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        print(f"-> PDF officiel généré avec succès ({len(pdf_content):,} octets) : {pdf_path}")

        # 5. Contrôle de non-régression sur les autres factures
        print("\n--- CONTRÔLE DE NON-RÉGRESSION SUR LES FACTURES EXISTANTES ---")
        m_consultant = env['btp.facture.modele'].search([('code', '=', 'honoraires_consultant')], limit=1)
        assert m_consultant, "Le modèle consultant doit toujours exister !"
        move_c = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': m_consultant.id,
            'honoraire_montant': 10000000.0,
            'honoraire_frais_remboursables': 2000000.0,
        })
        move_c._compute_honoraire_lines()
        assert move_c.honoraire_line_10_net_a_payer == 6400000.0, "Altération du modèle consultant !"
        print(f"-> Modèle Honoraires / Consultant: 100% Fonctionnel (Net: {move_c.honoraire_line_10_net_a_payer:,.0f} FCFA)")

        m_bordereau = env['btp.facture.modele'].search([('code', '=', 'bordereau_travaux')], limit=1)
        assert m_bordereau, "Le modèle bordereau doit toujours exister !"
        move_b = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': m_bordereau.id,
            'facture_amount_presente_ht': 1000000.0,
            'facture_marche_ht': 1000000.0,
        })
        move_b._compute_facture_bordereau_totals()
        assert move_b.facture_net_ttc == 590000.0, "Altération du modèle bordereau !"
        print(f"-> Modèle Bordereau de travaux: 100% Fonctionnel (Net TTC: {move_b.facture_net_ttc:,.0f} FCFA)")

        cr.rollback()
        print("\n=======================================================")
        print("TOUS LES TESTS DU MODÈLE ÉTUDES ONT RÉUSSI AVEC SUCCÈS !")
        print("=======================================================\n")

if __name__ == '__main__':
    run_test()
