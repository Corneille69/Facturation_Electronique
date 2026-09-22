# -*- coding: utf-8 -*-
import os
# pyrefly: ignore [missing-import]
import odoo
# pyrefly: ignore [missing-import]
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
        print("TEST: NOUVEAU MODÈLE « DÉCOMPTE DE TRAVAUX BTP »")
        print("=======================================================")

        # 1. Vérification du modèle dans la galerie
        modele = env['btp.facture.modele'].search([('code', '=', 'decompte_travaux_btp')], limit=1)
        assert modele, "Le modèle 'decompte_travaux_btp' doit exister dans btp.facture.modele !"
        assert modele.image_preview, "Le modèle 'decompte_travaux_btp' doit avoir son image de prévisualisation !"
        print(f"-> Modèle trouvé: '{modele.name}' (Code: {modele.code}) | Image: {len(modele.image_preview)} octets")

        # 2. Création d'un client et d'un marché d'exemple
        partner = env['res.partner'].search([('customer_rank', '>', 0)], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': 'Ministère des Infrastructures et du Désenclavement'})

        market = env['btp.market'].create({
            'name': 'N° 2026-088/MID/SG/DGI',
            'partner_id': partner.id,
            'objet': 'TRAVAUX DE RÉHABILITATION ET BITUMAGE DE LA VOIE INTER-URBAINE',
            'financement': "Budget de l'État (Exercice 2026)",
            'amount_untaxed': 100000000.0,
            'advance_rate': 20.0,
        })
        print(f"-> Marché créé: {market.name} | Montant HT: {market.amount_untaxed:,.0f} FCFA")

        # 3. CRÉATION DU PREMIER DÉCOMPTE (Décompte N° 1)
        print("\n--- 3. TEST DÉCOMPTE N° 1 (Avancement 35%) ---")
        move_1 = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': modele.id,
            'decompte_trv_market_id': market.id,
            'decompte_trv_numero': 'Décompte N° 1',
            'decompte_trv_marche_num': market.name,
            'decompte_trv_objet': market.objet,
            'decompte_trv_financement': market.financement,
            'decompte_trv_city': 'Ouagadougou',
            'decompte_trv_montant_marche_ht': 100000000.0,
            'decompte_trv_avancement_taux': 35.0,
            'decompte_trv_decomptes_precedents_ht': 0.0,
            'decompte_trv_avance_percue': 20000000.0,
        })
        move_1._compute_decompte_trv_marche_totals()
        move_1._compute_decompte_trv_values()

        print(f"Marché HT: {move_1.decompte_trv_montant_marche_ht:,.0f} FCFA")
        print(f"TVA Marché 18%: {move_1.decompte_trv_tva_marche:,.0f} FCFA")
        print(f"Marché TTC: {move_1.decompte_trv_montant_marche_ttc:,.0f} FCFA")
        print(f"Avancement: {move_1.decompte_trv_avancement_taux:.2f} %")
        print(f"Montant Cumulé HT: {move_1.decompte_trv_montant_cumule_ht:,.0f} FCFA")
        print(f"Décomptes Précédents: {move_1.decompte_trv_decomptes_precedents_ht:,.0f} FCFA")
        print(f"Montant Brut Décompte 1: {move_1.decompte_trv_montant_brut:,.0f} FCFA")
        print(f"Retenue garantie 5%: {move_1.decompte_trv_retenue_garantie:,.0f} FCFA")
        print(f"Retenue ARCOP 0,4%: {move_1.decompte_trv_retenue_arcop:,.0f} FCFA")
        print(f"Total retenues: {move_1.decompte_trv_total_retenues:,.0f} FCFA")
        print(f"Net HTVA: {move_1.decompte_trv_net_htva:,.0f} FCFA")
        print(f"TVA 18%: {move_1.decompte_trv_tva_decompte:,.0f} FCFA")
        print(f"Net TTC: {move_1.decompte_trv_net_ttc:,.0f} FCFA")
        print(f"Retenue Impôt 5%: {move_1.decompte_trv_retenue_impot_5:,.0f} FCFA")
        print(f"NET A PAYER: {move_1.decompte_trv_net_a_payer:,.0f} FCFA")
        print(f"Arrêté en lettres: {move_1.decompte_trv_net_lettres}")

        # Assertions Décompte 1
        assert move_1.decompte_trv_tva_marche == 18000000.0, "TVA Marché incorrecte"
        assert move_1.decompte_trv_montant_marche_ttc == 118000000.0, "Marché TTC incorrect"
        assert move_1.decompte_trv_montant_cumule_ht == 35000000.0, "Cumul HT incorrect"
        assert move_1.decompte_trv_montant_brut == 35000000.0, "Montant brut Décompte 1 incorrect"
        assert move_1.decompte_trv_retenue_garantie == 1750000.0, "Garantie 5% incorrecte"
        assert move_1.decompte_trv_retenue_arcop == 140000.0, "ARCOP 0.4% incorrecte"
        assert move_1.decompte_trv_total_retenues == 1890000.0, "Total retenues incorrect"
        assert move_1.decompte_trv_net_htva == 33110000.0, "Net HTVA incorrect"
        assert move_1.decompte_trv_tva_decompte == 5959800.0, "TVA Décompte incorrecte"
        assert move_1.decompte_trv_net_ttc == 39069800.0, "Net TTC incorrect"
        assert move_1.decompte_trv_retenue_impot_5 == 1655500.0, "Retenue impôt 5% incorrecte"
        assert move_1.decompte_trv_net_a_payer == 37414300.0, "NET A PAYER Décompte 1 incorrect"
        print("-> Décompte N° 1 : Toutes les formules mathématiques sont EXACTES !")

        # Validation comptable Décompte 1
        move_1.action_post()
        assert move_1.state == 'posted', "Décompte 1 doit être validé !"
        print(f"-> Décompte N° 1 validé en comptabilité: {move_1.name}")

        # 4. CRÉATION DU DEUXIÈME DÉCOMPTE (Décompte N° 2)
        print("\n--- 4. TEST DÉCOMPTE N° 2 (Avancement 70% avec reprise historique) ---")
        move_2 = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': modele.id,
            'decompte_trv_market_id': market.id,
            'decompte_trv_city': 'Ouagadougou',
            'decompte_trv_montant_marche_ht': 100000000.0,
            'decompte_trv_avancement_taux': 70.0,
            'decompte_trv_decomptes_precedents_ht': 35000000.0,
            'decompte_trv_avance_percue': 20000000.0,
        })
        move_2._compute_decompte_trv_marche_totals()
        move_2._compute_decompte_trv_values()

        print(f"Avancement: {move_2.decompte_trv_avancement_taux:.2f} %")
        print(f"Cumul HT (70%): {move_2.decompte_trv_montant_cumule_ht:,.0f} FCFA")
        print(f"Décomptes précédents perçus: {move_2.decompte_trv_decomptes_precedents_ht:,.0f} FCFA")
        print(f"Montant Brut Décompte 2 (70M - 35M): {move_2.decompte_trv_montant_brut:,.0f} FCFA")
        print(f"Retenue garantie 5%: {move_2.decompte_trv_retenue_garantie:,.0f} FCFA")
        print(f"Retenue ARCOP 0,4%: {move_2.decompte_trv_retenue_arcop:,.0f} FCFA")
        print(f"Net HTVA: {move_2.decompte_trv_net_htva:,.0f} FCFA")
        print(f"NET A PAYER: {move_2.decompte_trv_net_a_payer:,.0f} FCFA")

        # Assertions Décompte 2
        assert move_2.decompte_trv_montant_cumule_ht == 70000000.0, "Cumul HT Décompte 2 incorrect"
        assert move_2.decompte_trv_montant_brut == 35000000.0, "Montant brut Décompte 2 incorrect"
        assert move_2.decompte_trv_net_a_payer == 37414300.0, "NET A PAYER Décompte 2 incorrect"
        print("-> Décompte N° 2 : Reprise d'historique et calculs réussis avec succès !")

        move_2.action_post()
        assert move_2.state == 'posted', "Décompte 2 doit être validé !"
        print(f"-> Décompte N° 2 validé en comptabilité: {move_2.name}")

        # 5. TEST DE GÉNÉRATION DU RAPPORT PDF OFFICIEL
        print("\n--- 5. GÉNÉRATION DU RAPPORT PDF DÉCOMPTE DE TRAVAUX BTP ---")
        pdf_content, _ = env['ir.actions.report']._render_qweb_pdf(
            'btp_decompte.action_report_decompte_travaux',
            [move_2.id]
        )
        assert pdf_content and len(pdf_content) > 5000, f"Le PDF doit être généré ({len(pdf_content)} octets)"
        pdf_path = os.path.join(os.path.dirname(__file__), '..', 'facture_decompte_travaux_test.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        print(f"-> PDF officiel généré avec succès ({len(pdf_content):,} octets) : {pdf_path}")

        # 6. CONTRÔLE DE NON-RÉGRESSION SUR TOUS LES ANCIENS MODÈLES
        print("\n--- 6. CONTRÔLE DE NON-RÉGRESSION SUR LES AUTRES MODÈLES ---")
        # Bordereau travaux
        m_b = env['btp.facture.modele'].search([('code', '=', 'bordereau_travaux')], limit=1)
        assert m_b, "Modèle bordereau doit exister"
        mb = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': m_b.id,
            'facture_amount_presente_ht': 1000000.0,
            'facture_marche_ht': 1000000.0,
        })
        mb._compute_facture_bordereau_totals()
        assert mb.facture_net_ttc == 590000.0, "Altération modèle bordereau !"
        print("-> Modèle Bordereau: 100% Fonctionnel")

        # Honoraires Consultant
        m_c = env['btp.facture.modele'].search([('code', '=', 'honoraires_consultant')], limit=1)
        assert m_c, "Modèle consultant doit exister"
        mc = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': m_c.id,
            'honoraire_montant': 10000000.0,
            'honoraire_frais_remboursables': 2000000.0,
        })
        mc._compute_honoraire_lines()
        assert mc.honoraire_line_10_net_a_payer == 6400000.0, "Altération modèle consultant !"
        print("-> Modèle Honoraires Consultant: 100% Fonctionnel")

        # Honoraires Études
        m_e = env['btp.facture.modele'].search([('code', '=', 'honoraires_etudes')], limit=1)
        assert m_e, "Modèle études doit exister"
        me = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': m_e.id,
            'etude_marche_montant': 10000000.0,
        })
        me.action_init_default_etude_lines()
        assert len(me.etude_line_ids) == 10, "Altération modèle études !"
        print("-> Modèle Honoraires Études: 100% Fonctionnel")

        # Décompte BTP (15 lignes)
        m_d = env['btp.facture.modele'].search([('code', '=', 'decompte_btp')], limit=1)
        assert m_d, "Modèle décompte BTP doit exister"
        md = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': m_d.id,
            'decompte_btp_a': 100000000.0,
            'decompte_btp_b': 50.0,
            'decompte_btp_d': 0.0,
        })
        md._compute_decompte_btp_values()
        assert md.decompte_btp_c == 50000000.0, "Altération modèle Décompte BTP !"
        print("-> Modèle Décompte BTP (15 lignes): 100% Fonctionnel")

        cr.rollback()
        print("\n=======================================================")
        print("TOUS LES TESTS DU DÉCOMPTE DE TRAVAUX BTP ONT RÉUSSI !")
        print("=======================================================\n")

if __name__ == '__main__':
    run_test()
