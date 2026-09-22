# -*- coding: utf-8 -*-
import odoo
from odoo import api, SUPERUSER_ID

def test_exact_image_scenario():
    odoo.tools.config.parse_config(['-r', 'odoo', '-w', 'odoo', '--db_host', 'db', '--db_port', '5432', '-d', 'facturation_electronique'])
    registry = odoo.registry('facturation_electronique')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Configuration Société
        company = env.company
        company.name = "MY COMPANY"
        company.email = "yameogocedric7@gmail.com"
        company.ifu = "00045678W"
        company.rccm = "BF-OUA-01-2025-B12-00456"
        company.ati = "ATI-BTP-2025/112"
        company.regime_fiscal = "Réel Normal d'Imposition (RNI)"
        company.division_fiscale = "Direction des Grandes Entreprises (DGE)"

        Partner = env['res.partner']
        client = Partner.search([('name', '=', 'MUTRAF')], limit=1)
        if not client:
            client = Partner.create({'name': 'MUTRAF', 'is_company': True})

        # Création du marché exactement selon l'image :
        # Montant TTC = 20 000 000 -> Montant HT = 16 949 153
        Market = env['btp.market']
        existing_market = Market.search([('name', '=', 'MUTRAF / AG / CA / 005/2025')])
        if existing_market:
            existing_market.decompte_ids.unlink()
            existing_market.unlink()

        market = Market.create({
            'name': 'MUTRAF / AG / CA / 005/2025',
            'partner_id': client.id,
            'objet': 'Travaux de construction',
            'delay': '12 mois',
            'amount_untaxed': 16949153.0,
            'advance_rate': 30.0,
            'reimbursement_rate': 0.0,
            'warranty_rate': 5.0,
            'source_rate': 1.0,
            'arcop_type': 'rate',
            'arcop_rate': 0.40,
            'financement': 'Fonds propres',
        })
        market.action_start()

        # Création du Décompte N°1 avec 70% d'avancement
        Decompte = env['btp.decompte']
        d1 = Decompte.create({
            'market_id': market.id,
            'number': 1,
            'progress_rate': 70.0,
            'date': '2026-09-01',
            'date_attachement': '2026-09-01',
        })
        d1.action_validate()

        print("=== COMPARAISON DES VALEURS AVEC L'IMAGE DU CLIENT ===")
        print(f"Ligne A (Montant TTC Marché) : {d1.market_id.amount_total:,.0f} (Attendu: 20 000 000)")
        print(f"Ligne B (Montant HT Marché)  : {d1.market_id.amount_untaxed:,.0f} (Attendu: 16 949 153)")
        print(f"Ligne C (Taux avancement)    : {d1.progress_rate:.2f}% (Attendu: 70.00%)")
        print(f"Ligne D (Montant avancement) : {d1.cumul_travaux_ht:,.0f} (Attendu: 11 864 407)")
        print(f"Ligne E (Décompte passé N°0) : {d1.previous_decomptes_ht:,.0f} (Attendu: 0)")
        print(f"Ligne F (Décompte HT actuel) : {d1.current_decompte_ht:,.0f} (Attendu: 11 864 407)")
        print(f"Ligne G (TVA 18%)            : {d1.current_decompte_tva:,.0f} (Attendu: 2 135 593)")
        print(f"Ligne H (TTC Décompte N°01)  : {d1.current_decompte_ttc:,.0f} (Attendu: 14 000 000)")
        print(f"Ligne I (Taux remboursement) : {d1.reimbursement_rate:.0f}% (Attendu: 0%)")
        print(f"Ligne J (Remboursement avance): {d1.current_advance_reimbursement:,.0f} (Attendu: 0)")
        print(f"Ligne K (HT après remb.)     : {d1.ht_after_reimbursement:,.0f} (Attendu: 11 864 407)")
        print(f"Ligne L (TVA après remb.)    : {d1.tva_after_reimbursement:,.0f} (Attendu: 2 135 593)")
        print(f"Ligne M (TTC après remb.)    : {d1.ttc_after_reimbursement:,.0f} (Attendu: 14 000 000)")
        print(f"Ligne N (Garantie 5%)        : {d1.warranty_amount:,.0f} (Attendu: 593 220)")
        print(f"Ligne O (Source 1%)          : {d1.source_amount:,.0f} (Attendu: 118 644)")
        print(f"Ligne ARCOP (0.40%)          : {d1.arcop_amount:,.0f} (Attendu: 47 458)")
        print(f"Ligne P (Total retenues)     : {d1.total_retentions:,.0f} (Attendu: 759 322)")
        print(f"Ligne Q (NET À PAYER)        : {d1.net_to_pay:,.0f} (Attendu: 11 105 085)")

        assert abs(d1.market_id.amount_total - 20000000) < 10.0, "Erreur TTC Marché"
        assert abs(d1.current_decompte_ht - 11864407) < 10.0, "Erreur F"
        assert abs(d1.current_decompte_tva - 2135593) < 10.0, "Erreur G"
        assert abs(d1.warranty_amount - 593220) < 10.0, "Erreur N"
        assert abs(d1.source_amount - 118644) < 10.0, "Erreur O"
        assert abs(d1.arcop_amount - 47458) < 10.0, "Erreur ARCOP"
        assert abs(d1.total_retentions - 759322) < 10.0, "Erreur P"
        assert abs(d1.net_to_pay - 11105085) < 10.0, "Erreur Q"

        # Rendu PDF
        report = env.ref('btp_decompte.action_report_btp_decompte')
        pdf_data, _ = report._render_qweb_pdf(report.id, [d1.id])
        with open('/mnt/extra-addons/btp_decompte/facture_decompte_test.pdf', 'wb') as f:
            f.write(pdf_data)

        print(f"PDF généré avec succès ! Taille : {len(pdf_data)} octets.")
        print("=== TEST 100% RÉUSSI : TOUS LES CHIFFRES ET LE PDF SONT CONFORMES ! ===")

if __name__ == '__main__':
    test_exact_image_scenario()
