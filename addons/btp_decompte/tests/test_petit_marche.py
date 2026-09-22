# -*- coding: utf-8 -*-
import odoo
from odoo import api, SUPERUSER_ID

def test_petit_marche_flow():
    odoo.tools.config.parse_config(['-r', 'odoo', '-w', 'odoo', '--db_host', 'db', '--db_port', '5432', '-d', 'facturation_electronique'])
    registry = odoo.registry('facturation_electronique')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        print("==================================================")
        print("  TEST COMPLET DU MODÈLE PETITS MARCHÉS (SANS DÉCOMPTE)  ")
        print("==================================================")

        # 1. Client res.partner
        Partner = env['res.partner']
        client = Partner.search([('name', '=', 'CLIENT PETIT MARCHE TEST')], limit=1)
        if not client:
            client = Partner.create({
                'name': 'CLIENT PETIT MARCHE TEST',
                'is_company': True,
                'city': 'Ouagadougou',
            })
        print(f"1. Client vérifié : {client.name} (ID: {client.id})")

        # 2. Création du Petit Marché (Exemple officiel de la demande utilisateur)
        # Montant HT = 5 000 000 FCFA, Taux avance = 50 %
        PetitMarche = env['btp.petit.marche']
        existing = PetitMarche.search([('name', '=', 'PM-2025/TEST-001')])
        if existing:
            if existing.move_id:
                existing.move_id.unlink()
            existing.unlink()

        pm = PetitMarche.create({
            'name': 'PM-2025/TEST-001',
            'partner_id': client.id,
            'objet': 'Travaux de réfection toiture et peinture',
            'date': '2026-09-21',
            'amount_untaxed': 5000000.0,
            'advance_rate': 50.0,
        })
        print(f"2. Petit marché créé : {pm.name}")
        print(f"   - Montant HT : {pm.amount_untaxed:,.0f} {pm.currency_id.symbol}")
        print(f"   - TVA Marché (18%) : {pm.amount_tva:,.0f} {pm.currency_id.symbol}")
        print(f"   - Montant TTC Marché : {pm.amount_total:,.0f} {pm.currency_id.symbol}")
        print(f"   - Taux d'avance : {pm.advance_rate:.2f} %")
        print(f"   - Avance HT calculée : {pm.advance_amount_untaxed:,.0f} {pm.currency_id.symbol}")
        print(f"   - TVA sur l'avance (18%) : {pm.advance_tva:,.0f} {pm.currency_id.symbol}")
        print(f"   - Montant total à payer : {pm.amount_to_pay:,.0f} {pm.currency_id.symbol}")

        # VÉRIFICATIONS MATHÉMATIQUES EXACTES SELON L'EXEMPLE :
        assert abs(pm.amount_untaxed - 5000000.0) < 1.0, "Erreur Montant HT"
        assert abs(pm.amount_tva - 900000.0) < 1.0, "Erreur TVA Marché"
        assert abs(pm.amount_total - 5900000.0) < 1.0, "Erreur Montant TTC Marché (attendu 5 900 000)"
        assert abs(pm.advance_amount_untaxed - 2500000.0) < 1.0, "Erreur Avance HT (attendu 2 500 000)"
        assert abs(pm.advance_tva - 450000.0) < 1.0, "Erreur TVA sur avance (attendu 450 000)"
        assert abs(pm.amount_to_pay - 2950000.0) < 1.0, "Erreur Montant à payer (attendu 2 950 000)"
        print("   [OK] Tous les calculs de l'avance correspondent exactement aux formules de la demande !")

        # 3. Test des étapes de statut
        assert pm.state == 'draft', "L'état initial doit être draft"
        pm.action_compute()
        assert pm.state == 'computed', "L'état après calcul doit être computed"
        pm.action_validate()
        assert pm.state == 'validated', "L'état après validation doit être validated"
        print("3. Statut validé avec succès (Brouillon -> Calculé -> Validé)")

        # 4. Test de création de la facture client Odoo standard (account.move)
        pm.action_create_invoice()
        assert pm.move_id, "La facture Odoo doit être créée et liée au petit marché"
        assert pm.state == 'invoiced', "L'état doit passer à invoiced"
        invoice = pm.move_id
        print(f"4. Facture Odoo générée : {invoice.name or '/'} (ID: {invoice.id})")
        print(f"   - Type de document : {invoice.move_type} (out_invoice)")
        print(f"   - Client : {invoice.partner_id.name}")
        print(f"   - Lignes de facture : {len(invoice.invoice_line_ids)}")
        for line in invoice.invoice_line_ids:
            print(f"     * Libellé : {line.name[:50]}... | Prix HT : {line.price_unit:,.0f} | Sous-total : {line.price_subtotal:,.0f}")

        assert invoice.petit_marche_id.id == pm.id, "La facture doit être rattachée au petit marché"
        assert abs(invoice.amount_untaxed - 2500000.0) < 1.0, "Erreur montant HT facture"
        assert abs(invoice.amount_tax - 450000.0) < 1.0, "Erreur TVA facture"
        assert abs(invoice.amount_total - 2950000.0) < 1.0, "Erreur montant total facture (attendu 2 950 000)"
        print("   [OK] La facture Odoo standard reprend exactement l'avance HT (2 500 000), la TVA 18% (450 000) et le total (2 950 000) !")

        # 5. Test d'impression du rapport PDF QWeb Petit Marché
        report = env.ref('btp_decompte.action_report_btp_petit_marche')
        pdf_content, _ = report._render_qweb_pdf(report.id, [pm.id])
        with open('/mnt/extra-addons/btp_decompte/facture_petit_marche_test.pdf', 'wb') as f:
            f.write(pdf_content)
        assert len(pdf_content) > 1000, "Le PDF du petit marché doit être généré sans erreur"
        print(f"5. Rapport PDF généré avec succès ! Taille : {len(pdf_content)} octets")

        # 6. Test d'absence de logique de décomptes
        assert not hasattr(pm, 'decompte_ids'), "Le petit marché ne doit pas avoir de décomptes"
        assert not hasattr(pm, 'cumul_travaux_ht'), "Le petit marché ne doit pas avoir de cumul de travaux"
        assert not hasattr(pm, 'warranty_rate'), "Le petit marché ne doit pas avoir de retenue de garantie"
        print("6. [OK] Séparation totale validée : aucun champ ni logique de décompte dans les Petits Marchés !")

        # Nettoyage
        invoice.unlink()
        pm.unlink()
        client.unlink()
        print("==================================================")
        print("  TOUS LES TESTS PETITS MARCHÉS ONT RÉUSSI À 100% ! ")
        print("==================================================")

if __name__ == '__main__':
    test_petit_marche_flow()
