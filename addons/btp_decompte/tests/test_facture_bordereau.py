# -*- coding: utf-8 -*-
import os
import odoo
from odoo import api, fields
from odoo.tests.common import TransactionCase

def run_test():
    odoo.tools.config['db_name'] = 'facturation_electronique'
    odoo.tools.config['db_host'] = 'db'
    odoo.tools.config['db_user'] = 'odoo'
    odoo.tools.config['db_password'] = 'odoo'

    registry = odoo.registry('facturation_electronique')
    with registry.cursor() as cr:
        env = api.Environment(cr, odoo.SUPERUSER_ID, {})

        print("\n=======================================================")
        print("TEST: MODÈLES DE FACTURE ET FACTURE SPÉCIFIQUE BORDEREAU")
        print("=======================================================")

        # 1. Vérification des modèles de factures créés
        modeles = env['btp.facture.modele'].search([])
        print(f"-> Nombre de modèles de factures trouvés: {len(modeles)}")
        for m in modeles:
            has_img = bool(m.image_preview)
            print(f"   * [{m.code}] {m.name} | Image présente: {has_img} | Par défaut: {m.is_default}")
            if m.code in ('bordereau_travaux', 'grand_marche', 'petit_marche', 'standard'):
                assert has_img, f"Le modèle standard {m.name} doit avoir une image de prévisualisation !"

        modele_bordereau = env['btp.facture.modele'].search([('code', '=', 'bordereau_travaux')], limit=1)
        assert modele_bordereau, "Le modèle 'bordereau_travaux' doit exister !"

        # 2. Création d'une facture spécifique (sans nécessiter de grand ou petit marché)
        partner = env['res.partner'].search([('customer_rank', '>', 0)], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': 'Ministère des Infrastructures & Habitat'})

        move = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': modele_bordereau.id,
            'facture_city': 'Ouagadougou',
            'facture_objet': "TRAVAUX DE RÉFECTION ET DE PEINTURE DES BÂTIMENTS ADMINISTRATIFS",
            'facture_deduction_label': "Montant de la facture n°1 perçue de 50%",
            'facture_deduction_rate': 50.0,
            'facture_signatory': "Le Directeur Général",
            'invoice_line_ids': [
                (0, 0, {
                    'name': "Démolition et préparation des surfaces murales",
                    'quantity': 100.0,
                    'price_unit': 5000.0,
                    'price_subtotal': 500000.0,
                    'montant_marche_ht': 600000.0,
                }),
                (0, 0, {
                    'name': "Application peinture acrylique deux couches",
                    'quantity': 200.0,
                    'price_unit': 7500.0,
                    'price_subtotal': 1500000.0,
                    'montant_marche_ht': 1800000.0,
                }),
            ]
        })

        # Forcer le recalcul
        print(f"Lines count: {len(move.invoice_line_ids)}")
        for l in move.invoice_line_ids:
            print(f"   Line: name={l.name}, display_type={l.display_type}, qty={l.quantity}, price_unit={l.price_unit}, price_subtotal={l.price_subtotal}")
        move._compute_facture_bordereau_totals()
        move._compute_facture_bordereau_words()
        move._compute_facture_bordereau_html()

        print(f"\n-> Facture ID: {move.id}")
        print(f"-> Modèle code: {move.facture_modele_code}")
        print(f"-> Présente facture HT: {move.facture_amount_presente_ht} (Attendu: 2 000 000)")
        assert move.facture_amount_presente_ht == 2000000.0, f"Erreur montant présent HT: {move.facture_amount_presente_ht}"

        print(f"-> Déduction 50%: {move.facture_deduction_amount} (Attendu: -1 000 000)")
        assert move.facture_deduction_amount == -1000000.0, f"Erreur montant déduction: {move.facture_deduction_amount}"

        print(f"-> Net HT: {move.facture_net_ht} (Attendu: 1 000 000)")
        assert move.facture_net_ht == 1000000.0, f"Erreur montant net HT: {move.facture_net_ht}"

        print(f"-> TVA 18%: {move.facture_tva_18} (Attendu: 180 000)")
        assert move.facture_tva_18 == 180000.0, f"Erreur montant TVA 18%: {move.facture_tva_18}"

        print(f"-> Net TTC: {move.facture_net_ttc} (Attendu: 1 180 000)")
        assert move.facture_net_ttc == 1180000.0, f"Erreur montant TTC: {move.facture_net_ttc}"

        print(f"-> Arrêté en toutes lettres: {move.facture_net_ttc_words}")
        assert "cent" in move.facture_net_ttc_words.lower() or "mille" in move.facture_net_ttc_words.lower()

        # 3. Test de génération du rapport PDF
        print("\n-> Test génération du PDF Facture Bordereau...")
        report_action = env.ref('btp_decompte.action_report_facture_bordereau')
        pdf_content, _ = report_action._render_qweb_pdf(report_action.id, [move.id])
        print(f"-> PDF généré avec succès ! Taille: {len(pdf_content)} octets")
        assert len(pdf_content) > 1000, "Le PDF généré doit contenir des données valides."

        # Sauvegarde temporaire pour inspection visuelle
        pdf_path = "/tmp/test_facture_bordereau.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        print(f"-> PDF écrit dans {pdf_path}")

        # 4. Test SCÉNARIO UTILISATEUR : Saisie UNIQUEMENT du Montant Principal
        print("\n-------------------------------------------------------")
        print("TEST SCÉNARIO UTILISATEUR : SAISIE DIRECTE DU MONTANT PRINCIPAL")
        print("-------------------------------------------------------")
        move_direct = env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'facture_modele_id': modele_bordereau.id,
            'facture_city': 'Ouagadougou',
            'facture_objet': "TRAVAUX DE PEINTURE ET RÉFECTION",
            'facture_amount_presente_ht': 5000000.0,
            'facture_deduction_rate': 50.0,
            'facture_tva_rate': 18.0,
        })
        move_direct._compute_facture_bordereau_totals()
        move_direct._compute_facture_bordereau_words()
        move_direct._compute_facture_bordereau_html()

        print(f"-> Facture directe ID: {move_direct.id}")
        print(f"-> Montant Principal HT: {move_direct.facture_amount_presente_ht} (Attendu: 5 000 000)")
        assert move_direct.facture_amount_presente_ht == 5000000.0
        print(f"-> Déduction 50%: {move_direct.facture_deduction_amount} (Attendu: -2 500 000)")
        assert move_direct.facture_deduction_amount == -2500000.0
        print(f"-> Net HT: {move_direct.facture_net_ht} (Attendu: 2 500 000)")
        assert move_direct.facture_net_ht == 2500000.0
        print(f"-> TVA 18%: {move_direct.facture_tva_18} (Attendu: 450 000)")
        assert move_direct.facture_tva_18 == 450000.0
        print(f"-> Net TTC: {move_direct.facture_net_ttc} (Attendu: 2 950 000)")
        assert move_direct.facture_net_ttc == 2950000.0
        print(f"-> En lettres: {move_direct.facture_net_ttc_words}")
        print(f"-> Lignes générées automatiquement: {len(move_direct.invoice_line_ids)}")
        assert len(move_direct.invoice_line_ids) >= 1

        # Test génération PDF pour cette facture saisie directement
        pdf_direct, _ = report_action._render_qweb_pdf(report_action.id, [move_direct.id])
        assert len(pdf_direct) > 1000
        print(f"-> PDF direct généré avec succès ! Taille: {len(pdf_direct)} octets")

        print("\n>>> TOUS LES TESTS FACTURE BORDEREAU ET MODÈLES ONT RÉUSSI AVEC SUCCÈS ! <<<")

if __name__ == '__main__':
    run_test()
