# -*- coding: utf-8 -*-
import odoo
from odoo import api, SUPERUSER_ID

def test_no_negative_amounts():
    odoo.tools.config.parse_config(['-r', 'odoo', '-w', 'odoo', '--db_host', 'db', '--db_port', '5432', '-d', 'facturation_electronique'])
    registry = odoo.registry('facturation_electronique')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        print("=== TEST VÉRIFICATION DE NON-NÉGATIVITÉ DES MONTANTS ===")
        Partner = env['res.partner']
        client = Partner.search([('name', '=', 'CLIENT TEST SAFEGUARD')], limit=1)
        if not client:
            client = Partner.create({'name': 'CLIENT TEST SAFEGUARD', 'is_company': True})

        Market = env['btp.market']
        market = Market.create({
            'name': 'MARCHE-TEST-SAFEGUARD-001',
            'partner_id': client.id,
            'objet': 'Travaux de voirie et terrassement',
            'delay': '12 mois',
            'amount_untaxed': 100000000.0, # 100M
            'advance_rate': 30.0,           # 30M
            'reimbursement_rate': 50.0,     # 15M par décompte théorique
            'warranty_rate': 5.0,
            'source_rate': 1.0,
        })
        market.action_start()

        Decompte = env['btp.decompte']
        # Décompte 1 à 30%
        d1 = Decompte.create({
            'market_id': market.id,
            'number': 1,
            'progress_rate': 30.0,
        })
        d1.action_validate()
        print(f"Décompte 1 validé: Cumul={d1.cumul_travaux_ht:,.0f}, Actuel={d1.current_decompte_ht:,.0f}, Net={d1.net_to_pay:,.0f}")
        assert d1.net_to_pay >= 0, "Net à payer D1 doit être >= 0"

        # Décompte 2 ouvert en brouillon avec taux à 0 ou non renseigné
        d2 = Decompte.new({
            'market_id': market.id,
            'number': 2,
            'progress_rate': 0.0,
        })
        d2._compute_travaux_amounts()
        d2._compute_tva_amounts()
        d2._compute_advance_amounts()
        d2._compute_after_reimbursement()
        d2._compute_retentions()
        d2._compute_net_to_pay()

        print(f"Décompte 2 en cours de saisie (taux=0%):")
        print(f"  - Décompte HT actuel : {d2.current_decompte_ht:,.0f}")
        print(f"  - HT après remboursement : {d2.ht_after_reimbursement:,.0f}")
        print(f"  - Net à payer : {d2.net_to_pay:,.0f}")

        assert d2.current_decompte_ht >= 0, "Décompte HT actuel ne doit JAMAIS être négatif !"
        assert d2.ht_after_reimbursement >= 0, "HT après remboursement ne doit JAMAIS être négatif !"
        assert d2.net_to_pay >= 0, "Net à payer ne doit JAMAIS être négatif !"

        # Décompte 2 avec taux d'avancement = 60%
        d2_saved = Decompte.create({
            'market_id': market.id,
            'number': 2,
            'progress_rate': 60.0,
        })
        print(f"Décompte 2 avec taux global 60%:")
        print(f"  - Décomptes passés : {d2_saved.previous_decomptes_ht:,.0f}")
        print(f"  - Décompte HT actuel : {d2_saved.current_decompte_ht:,.0f}")
        print(f"  - HT après remboursement : {d2_saved.ht_after_reimbursement:,.0f}")
        print(f"  - Net à payer : {d2_saved.net_to_pay:,.0f}")

        assert d2_saved.previous_decomptes_ht == 30000000.0
        assert d2_saved.current_decompte_ht == 30000000.0
        assert d2_saved.ht_after_reimbursement > 0
        assert d2_saved.net_to_pay > 0

        # Nettoyage
        d2_saved.unlink()
        d1.unlink()
        market.unlink()
        client.unlink()
        print("=== TEST GARDE-FOUS ANTI-NÉGATIFS 100% RÉUSSI ===")

if __name__ == '__main__':
    test_no_negative_amounts()
