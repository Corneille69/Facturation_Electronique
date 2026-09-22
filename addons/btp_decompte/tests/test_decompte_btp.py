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
        print("TEST: NOUVEAU MODÈLE FACTURE / DÉCOMPTE BTP")
        print("=======================================================")

        # 1. Vérification du modèle dans la galerie
        modele = env['btp.facture.modele'].search([('code', '=', 'decompte_btp')], limit=1)
        assert modele, "Le modèle 'decompte_btp' doit exister dans btp.facture.modele !"
        assert modele.image_preview, "Le modèle 'decompte_btp' doit avoir son image de prévisualisation !"
        print(f"-> Modèle trouvé: '{modele.name}' (Code: {modele.code}) | Image: {len(modele.image_preview)} octets")

        # 2. Création d'une facture client avec ce modèle
        partner = env['res.partner'].search([('customer_rank', '>', 0)], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': 'Ministère des Infrastructures et du Désenclavement'})

        move = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': modele.id,
            'decompte_btp_city': 'Ouagadougou',
            'decompte_btp_marche_num': 'N° 2026-088/MID/SG/DGI',
            'decompte_btp_financement': "Budget de l'État (Exercice 2026)",
            'decompte_btp_objet': 'TRAVAUX DE RÉHABILITATION ET BITUMAGE DE LA VOIE INTER-URBAINE',
            'decompte_btp_signataire_titre': 'Le Bureau',
            'decompte_btp_signataire_nom': 'BUREAU DE CONTRÔLE & EXPERTISE BTP',
            'decompte_btp_a': 336005138.0,
            'decompte_btp_b': 66.50,
            'decompte_btp_d': 84001285.0,
            'decompte_btp_f': 0.0,
        })

        # Recalculer les formules
        move._compute_decompte_btp_values()

        print("\n--- VÉRIFICATION DES FORMULES MATHÉMATIQUES BTP (A à TR) ---")
        print(f"(A) Montant du Marché HTVA: {move.decompte_btp_a:,.2f} FCFA")
        print(f"(B) Taux d'avancement: {move.decompte_btp_b:.4f} %")
        print(f"(C) = (TA) x (MHTVA): {move.decompte_btp_c:,.2f} FCFA")
        print(f"(D) Décomptes précédents: {move.decompte_btp_d:,.2f} FCFA")
        print(f"(MB) = (C) - (D) [Montant Brut]: {move.decompte_btp_mb:,.2f} FCFA")
        print(f"(E) = A x 20% [Avance démarrage]: {move.decompte_btp_e:,.2f} FCFA")
        print(f"(F) Remboursement avances préc.: {move.decompte_btp_f:,.2f} FCFA")
        print(f"(G) Remboursement avance décompte: {move.decompte_btp_g:,.2f} FCFA")
        print(f"(H) Retenue source 5%: {move.decompte_btp_h:,.2f} FCFA")
        print(f"(I) Retenue ARCOP 0.4%: {move.decompte_btp_i:,.2f} FCFA")
        print(f"(TR) Total Retenues (G + H + I): {move.decompte_btp_tr:,.2f} FCFA")
        print(f"NET HTVA = MB - TR: {move.decompte_btp_net_htva:,.2f} FCFA")
        print(f"TVA 18%: {move.decompte_btp_tva:,.2f} FCFA")
        print(f"NET TTC = Net HTVA + TVA: {move.decompte_btp_net_ttc:,.2f} FCFA")
        print(f"Arrêté en lettres: {move.decompte_btp_net_lettres}")

        # Assertions strictes basées sur les données réelles du document fourni
        # C = 336 005 138 * 0.665 = 223 443 416.77 -> arrondi à l'unité = 223 443 417
        assert abs(move.decompte_btp_c - 223443417.0) < 1.0, f"C incorrect: {move.decompte_btp_c}"
        assert abs(move.decompte_btp_mb - 139442132.0) < 1.0, f"MB incorrect: {move.decompte_btp_mb}"
        assert abs(move.decompte_btp_e - 67201028.0) < 1.0, f"E incorrect: {move.decompte_btp_e}"
        # G = 67 201 027.6 * (66.5 - 20) / 60 = 52 080 796.39 -> arrondi = 52 080 796
        assert abs(move.decompte_btp_g - 52080796.0) < 1.0, f"G incorrect: {move.decompte_btp_g}"
        # H = 139 442 131.77 * 0.05 = 6 972 106.59 -> arrondi = 6 972 107
        assert abs(move.decompte_btp_h - 6972107.0) < 1.0, f"H incorrect: {move.decompte_btp_h}"
        # I = 336 005 138 * 0.004 = 1 344 020.55 -> arrondi = 1 344 021
        assert abs(move.decompte_btp_i - 1344021.0) < 1.0, f"I incorrect: {move.decompte_btp_i}"
        # TR = 52 080 796 + 6 972 107 + 1 344 021 = 60 396 924
        assert abs(move.decompte_btp_tr - 60396924.0) < 1.0, f"TR incorrect: {move.decompte_btp_tr}"
        # Net HTVA = 139 442 132 - 60 396 924 = 79 045 208
        assert abs(move.decompte_btp_net_htva - 79045208.0) < 1.0, f"Net HTVA incorrect: {move.decompte_btp_net_htva}"
        # TVA 18% = 79 045 208 * 0.18 = 14 228 137.44 -> arrondi = 14 228 137
        assert abs(move.decompte_btp_tva - 14228137.0) < 1.0, f"TVA incorrecte: {move.decompte_btp_tva}"
        # Net TTC = 79 045 208 + 14 228 137 = 93 273 345 ou 93 273 346
        assert abs(move.decompte_btp_net_ttc - 93273345.0) <= 1.0, f"Net TTC incorrect: {move.decompte_btp_net_ttc}"
        assert 'quatre-vingt-treize millions' in move.decompte_btp_net_lettres.lower(), f"Texte en lettres incorrect: {move.decompte_btp_net_lettres}"
        print("-> Toutes les formules mathématiques (A à TR, TVA, Net TTC) sont vérifiées avec exactitude !")

        # 3. Synchronisation des lignes comptables et validation (action_post)
        print("\n--- VALIDATION COMPTABLE DE LA FACTURE ---")
        move.action_post()
        assert move.state == 'posted', "La facture Décompte BTP doit pouvoir être validée comptablement !"
        print(f"-> Facture validée avec succès: Statut = {move.state}, Numéro = {move.name}")

        # 4. Test d'impression du rapport PDF officiel
        print("\n--- GÉNÉRATION DU RAPPORT PDF OFFICIEL DÉCOMPTE BTP ---")
        pdf_content, _ = env['ir.actions.report']._render_qweb_pdf(
            'btp_decompte.action_report_facture_decompte',
            [move.id]
        )
        assert pdf_content and len(pdf_content) > 5000, f"Le PDF doit être généré et non vide ({len(pdf_content)} octets)"
        pdf_path = os.path.join(os.path.dirname(__file__), '..', 'facture_decompte_btp_test.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        print(f"-> PDF officiel Décompte BTP généré avec succès ({len(pdf_content):,} octets) : {pdf_path}")

        # 5. Contrôle de non-régression sur les factures existantes
        print("\n--- CONTRÔLE DE NON-RÉGRESSION SUR TOUTES LES AUTRES FACTURES ---")
        # Modèle Bordereau Travaux
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
        print(f"-> Modèle Bordereau: OK (Net TTC = {move_b.facture_net_ttc:,.0f} FCFA)")

        # Modèle Honoraires Consultant
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
        print(f"-> Modèle Honoraires Consultant: OK (Net = {move_c.honoraire_line_10_net_a_payer:,.0f} FCFA)")

        # Modèle Honoraires Études
        m_etudes = env['btp.facture.modele'].search([('code', '=', 'honoraires_etudes')], limit=1)
        assert m_etudes, "Le modèle études doit toujours exister !"
        move_e = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': m_etudes.id,
            'etude_marche_montant': 10000000.0,
        })
        move_e.action_init_default_etude_lines()
        assert len(move_e.etude_line_ids) == 10, "Altération du modèle études !"
        print(f"-> Modèle Honoraires Études: OK ({len(move_e.etude_line_ids)} lignes types)")

        cr.rollback()
        print("\n=======================================================")
        print("TOUS LES TESTS DU MODÈLE DÉCOMPTE BTP ONT RÉUSSI AVEC SUCCÈS !")
        print("=======================================================\n")

if __name__ == '__main__':
    run_test()
