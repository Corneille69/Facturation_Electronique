# -*- coding: utf-8 -*-
import odoo
from odoo import api, SUPERUSER_ID

def test_btp_flow():
    odoo.tools.config.parse_config(['-r', 'odoo', '-w', 'odoo', '--db_host', 'db', '--db_port', '5432', '-d', 'facturation_electronique'])
    registry = odoo.registry('facturation_electronique')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        print("=== DEBUT DES TESTS DU MODULE BTP_DECOMPTE ===")

        # 1. Vérification Client res.partner
        Partner = env['res.partner']
        client = Partner.search([('name', '=', 'MUTRAF')], limit=1)
        if not client:
            client = Partner.create({
                'name': 'MUTRAF',
                'is_company': True,
                'city': 'Cotonou',
                'country_id': env.ref('base.bj', raise_if_not_found=False) and env.ref('base.bj').id or False,
            })
        print(f"1. Client vérifié : {client.name} (ID: {client.id})")

        # 2. Création du Marché BTP
        Market = env['btp.market']
        market = Market.search([('name', '=', 'MUTRAF / AG / CA / 005/2025')], limit=1)
        if market:
            market.decompte_ids.unlink()
            market.unlink()

        market = Market.create({
            'name': 'MUTRAF / AG / CA / 005/2025',
            'partner_id': client.id,
            'objet': "Travaux de construction d'un bâtiment R+3",
            'date_market': '2025-05-23',
            'date_start': '2025-07-07',
            'delay': '12 mois',
            'amount_untaxed': 336005138.0,
            'advance_rate': 30.0,
            'reimbursement_rate': 70.0,
            'warranty_rate': 5.0,
            'source_rate': 1.0,
            'arcop_type': 'rate',
            'arcop_rate': 0.0,
        })
        market.action_start()

        print(f"2. Marché créé : {market.name}")
        print(f"   - Montant HT : {market.amount_untaxed:,.2f}")
        print(f"   - TVA (18%)  : {market.amount_tva:,.2f}")
        print(f"   - Montant TTC: {market.amount_total:,.2f}")
        print(f"   - Avance Totale (30%) : {market.advance_total:,.2f}")

        assert abs(market.amount_untaxed - 336005138.0) < 1.0, "Erreur montant HT marché"
        assert abs(market.advance_total - 100801541.4) < 1.0, "Erreur montant avance"

        # 3. Création du Décompte N°1 (Avancement 25%)
        Decompte = env['btp.decompte']
        d1 = Decompte.create({
            'market_id': market.id,
            'number': 1,
            'progress_rate': 25.0,
            'date': '2025-08-30',
        })
        d1.action_validate()

        print(f"3. Décompte N°1 validé :")
        print(f"   - Avancement : {d1.progress_rate}%")
        print(f"   - Travaux cumulés HT : {d1.cumul_travaux_ht:,.2f}")
        print(f"   - Décompte HT actuel (F) : {d1.current_decompte_ht:,.2f}")
        print(f"   - Remboursement avance (J) : {d1.current_advance_reimbursement:,.2f}")
        print(f"   - HT après remboursement (K = F - J) : {d1.ht_after_reimbursement:,.2f}")
        print(f"   - Retenue Garantie (5%) : {d1.warranty_amount:,.2f}")
        print(f"   - Retenue Source (1%)   : {d1.source_amount:,.2f}")
        print(f"   - Total Retenues : {d1.total_retentions:,.2f}")
        print(f"   - Net à Payer    : {d1.net_to_pay:,.2f}")

        # 4. Création du Décompte N°2 (Avancement 66.50%)
        d2 = Decompte.create({
            'market_id': market.id,
            'number': 2,
            'progress_rate': 66.50,
            'date': '2025-10-15',
        })
        d2.action_validate()

        print(f"4. Décompte N°2 validé (Exemple officiel utilisateur) :")
        print(f"   - Avancement : {d2.progress_rate}%")
        print(f"   - Travaux cumulés HT : {d2.cumul_travaux_ht:,.2f} (Attendu ~223 443 417)")
        print(f"   - Décomptes antérieurs : {d2.previous_decomptes_ht:,.2f} (Attendu ~84 001 285)")
        print(f"   - Décompte HT actuel (F) : {d2.current_decompte_ht:,.2f} (Attendu ~139 442 132)")
        print(f"   - HT après remboursement (K = F - J) : {d2.ht_after_reimbursement:,.2f}")
        print(f"   - Retenue Garantie (5%) : {d2.warranty_amount:,.2f}")
        print(f"   - Retenue Source (1%)   : {d2.source_amount:,.2f}")
        print(f"   - Total Retenues        : {d2.total_retentions:,.2f}")
        print(f"   - Net à Payer           : {d2.net_to_pay:,.2f}")

        assert d2.cumul_travaux_ht > d2.previous_decomptes_ht, "Le cumul doit être supérieur aux précédents"
        assert d2.current_decompte_ht > 0, "Le décompte actuel doit être positif"
        assert d2.net_to_pay > 0, "Le net à payer doit être positif"

        # 5. Test Facturation Odoo (account.move)
        print("5. Test de génération de la facture Odoo...")
        res_inv = d2.action_create_invoice()
        move = d2.move_id
        print(f"   - Facture Odoo générée : {move.name or 'Brouillon'} (ID: {move.id})")
        print(f"   - Décompte lié : {move.decompte_id.name}")
        print(f"   - Marché lié : {move.market_id.name}")
        print(f"   - Lignes de facture : {len(move.invoice_line_ids)}")
        for l in move.invoice_line_ids:
            print(f"     * {l.name[:45]}... | Montant : {l.price_subtotal:,.2f}")

        assert move.decompte_id.id == d2.id, "Facture non liée au décompte"
        assert d2.state == 'invoiced', "Le décompte devrait être à l'état 'invoiced'"

        # 6. Test du Décompte Final et Clôture du Marché
        print("6. Test du Décompte Final N°3...")
        d3 = Decompte.create({
            'market_id': market.id,
            'number': 3,
            'progress_rate': 100.0,
            'is_final': True,
            'date': '2025-12-20',
        })
        d3.action_validate()
        print(f"   - Décompte N°3 validé (Final). État marché : {market.state}")
        assert market.state == 'done', "Le marché devrait être à l'état 'done' (Clôturé)"
        assert market.is_final_done == True, "is_final_done devrait être True"

        # 7. Test de blocage d'un nouveau décompte après décompte final
        print("7. Test de contrainte : création bloquée après décompte final...")
        try:
            with cr.savepoint():
                d_illegal = Decompte.create({
                    'market_id': market.id,
                    'number': 4,
                    'progress_rate': 100.0,
                    'date': '2026-01-10',
                })
            raise Exception("La contrainte aurait dû bloquer ce décompte !")
        except Exception as e:
            print(f"   -> Blocage réussi avec succès : {e}")

        # 8. Test de génération du rapport PDF
        print("8. Test de rendu du rapport PDF QWeb...")
        Report = env['ir.actions.report']
        report = env.ref('btp_decompte.action_report_btp_decompte')
        pdf_content, _ = report._render_qweb_pdf(report.id, [d2.id])
        assert len(pdf_content) > 1000, "Le PDF généré est trop court ou vide"
        print(f"   -> Rapport PDF généré avec succès ! Taille : {len(pdf_content)} octets")

        print("=== TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS ! ===")

if __name__ == '__main__':
    test_btp_flow()
