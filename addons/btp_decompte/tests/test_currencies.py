# -*- coding: utf-8 -*-
import odoo
from odoo import api, SUPERUSER_ID

def test_currencies_feature():
    odoo.tools.config.parse_config(['-r', 'odoo', '-w', 'odoo', '--db_host', 'db', '--db_port', '5432', '-d', 'facturation_electronique'])
    registry = odoo.registry('facturation_electronique')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        print("==================================================")
        print("  TEST COMPLET DES DEVISES : FCFA, DOLLAR, EURO   ")
        print("==================================================")

        # 1. Vérification de l'activation et des attributs des devises
        Currency = env['res.currency']
        xof = Currency.search([('name', '=', 'XOF')])
        eur = Currency.search([('name', '=', 'EUR')])
        usd = Currency.search([('name', '=', 'USD')])

        print("\n--- 1. ÉTAT DES DEVISES ---")
        assert xof and xof.active, "La devise FCFA (XOF) doit être active"
        assert eur and eur.active, "La devise EUR doit être active"
        assert usd and usd.active, "La devise USD doit être active"
        assert xof.symbol == 'FCFA', f"Le symbole de XOF doit être FCFA, obtenu: {xof.symbol}"
        assert eur.symbol == '€', f"Le symbole de EUR doit être €, obtenu: {eur.symbol}"
        assert usd.symbol == '$', f"Le symbole de USD doit être $, obtenu: {usd.symbol}"

        print(f"  [OK] FCFA (XOF) : active={xof.active}, symbol={xof.symbol}, sequence={xof.sequence}")
        print(f"  [OK] EUR        : active={eur.active}, symbol={eur.symbol}, sequence={eur.sequence}")
        print(f"  [OK] USD        : active={usd.active}, symbol={usd.symbol}, sequence={usd.sequence}")

        # 2. Vérification de l'ordre de tri (FCFA en premier)
        print("\n--- 2. ORDRE DE TRI DES DEVISES ---")
        active_currencies = Currency.search([('name', 'in', ('XOF', 'EUR', 'USD'))])
        print("  Ordre retourné par search() :", [c.name for c in active_currencies])
        assert active_currencies[0].name == 'XOF', f"Le FCFA doit être la première devise retournée, obtenu: {active_currencies[0].name}"
        print("  [OK] FCFA est bien en première position par défaut !")

        # 3. Vérification des libellés (display_name) et de la recherche
        print("\n--- 3. AFFICHAGE ET RECHERCHE ---")
        print(f"  display_name XOF : {xof.display_name}")
        print(f"  display_name EUR : {eur.display_name}")
        print(f"  display_name USD : {usd.display_name}")
        assert "FCFA" in xof.display_name, "display_name de XOF doit contenir FCFA"
        assert "EUR" in eur.display_name or "€" in eur.display_name
        assert "USD" in usd.display_name or "$" in usd.display_name

        search_fcfa = Currency.name_search('FCFA')
        assert any(r[0] == xof.id for r in search_fcfa), "Recherche 'FCFA' doit trouver XOF"
        print(f"  [OK] Recherche 'FCFA' trouvée : {search_fcfa}")

        # 4. Vérification de la devise par défaut de la société
        print("\n--- 4. DEVISE DE LA SOCIÉTÉ ---")
        company = env.company
        print(f"  Société : {company.name}, Devise : {company.currency_id.name} ({company.currency_id.symbol})")
        assert company.currency_id.name in ('XOF', 'XAF'), f"La devise société doit être FCFA, obtenu: {company.currency_id.name}"
        print("  [OK] La société a bien le FCFA par défaut !")

        # 5. Création d'un marché avec devise par défaut (FCFA)
        print("\n--- 5. MARCHÉ AVEC DEVISE PAR DÉFAUT (FCFA) ---")
        Partner = env['res.partner']
        client = Partner.search([('name', '=', 'CLIENT_TEST_DEVISES')], limit=1)
        if not client:
            client = Partner.create({'name': 'CLIENT_TEST_DEVISES', 'is_company': True})

        Market = env['btp.market']
        market_default = Market.create({
            'name': 'MARCHE-TEST-FCFA-DEFAULT',
            'partner_id': client.id,
            'objet': 'Test marché par défaut en FCFA',
            'amount_untaxed': 50000000.0,
        })
        assert market_default.currency_id.name in ('XOF', 'XAF'), f"Le marché par défaut doit être en FCFA, obtenu: {market_default.currency_id.name}"
        print(f"  [OK] Marché créé : {market_default.name}, Devise : {market_default.currency_id.display_name}")

        # 6. Création d'un marché avec choix explicite de l'Euro (EUR)
        print("\n--- 6. MARCHÉ AVEC CHOIX EXPLICITE DE L'EURO (EUR) ---")
        market_eur = Market.create({
            'name': 'MARCHE-TEST-EUR',
            'partner_id': client.id,
            'objet': 'Test marché en Euro',
            'currency_id': eur.id,
            'amount_untaxed': 100000.0,
        })
        assert market_eur.currency_id.id == eur.id, "Le marché doit être en Euro"
        market_eur.action_start()
        print(f"  [OK] Marché créé : {market_eur.name}, Devise : {market_eur.currency_id.display_name}")

        # Création d'un décompte sur le marché Euro
        Decompte = env['btp.decompte']
        d_eur = Decompte.create({
            'market_id': market_eur.id,
            'number': 1,
            'progress_rate': 50.0,
            'date': '2026-09-15',
        })
        d_eur.action_validate()
        assert d_eur.currency_id.id == eur.id, "Le décompte doit hériter de la devise Euro"
        print(f"  [OK] Décompte N°{d_eur.number} créé en EUR : Net à payer = {d_eur.net_to_pay:,.2f} {d_eur.currency_id.symbol}")

        # Facture Odoo en Euro
        d_eur.action_create_invoice()
        assert d_eur.move_id, "La facture Odoo doit être générée"
        assert d_eur.move_id.currency_id.id == eur.id, "La facture doit être en Euro"
        print(f"  [OK] Facture Odoo générée en EUR : {d_eur.move_id.name}, Devise : {d_eur.move_id.currency_id.symbol}")

        # 7. Création d'un marché avec choix explicite du Dollar (USD)
        print("\n--- 7. MARCHÉ AVEC CHOIX EXPLICITE DU DOLLAR (USD) ---")
        market_usd = Market.create({
            'name': 'MARCHE-TEST-USD',
            'partner_id': client.id,
            'objet': 'Test marché en Dollar',
            'currency_id': usd.id,
            'amount_untaxed': 75000.0,
        })
        assert market_usd.currency_id.id == usd.id, "Le marché doit être en Dollar"
        market_usd.action_start()
        print(f"  [OK] Marché créé : {market_usd.name}, Devise : {market_usd.currency_id.display_name}")

        d_usd = Decompte.create({
            'market_id': market_usd.id,
            'number': 1,
            'progress_rate': 40.0,
            'date': '2026-09-15',
        })
        d_usd.action_validate()
        assert d_usd.currency_id.id == usd.id, "Le décompte doit être en Dollar"
        print(f"  [OK] Décompte N°{d_usd.number} créé en USD : Net à payer = {d_usd.net_to_pay:,.2f} {d_usd.currency_id.symbol}")

        # 8. Test Rendu PDF pour chaque devise
        print("\n--- 8. TEST GÉNÉRATION DES RAPPORTS PDF ---")
        report = env.ref('btp_decompte.action_report_btp_decompte')

        # Test PDF EUR
        pdf_eur, _ = report._render_qweb_pdf(report.id, [d_eur.id])
        assert len(pdf_eur) > 1000, "Le PDF EUR doit être généré"
        print(f"  [OK] PDF Décompte EUR généré avec succès ({len(pdf_eur)} octets)")

        # Test PDF USD
        pdf_usd, _ = report._render_qweb_pdf(report.id, [d_usd.id])
        assert len(pdf_usd) > 1000, "Le PDF USD doit être généré"
        print(f"  [OK] PDF Décompte USD généré avec succès ({len(pdf_usd)} octets)")

        # Nettoyage des données de test
        if d_eur.move_id:
            d_eur.move_id.unlink()
        d_eur.unlink()
        market_eur.unlink()

        d_usd.unlink()
        market_usd.unlink()
        market_default.unlink()
        client.unlink()

        cr.commit()
        print("\n==================================================")
        print("  TOUS LES TESTS DE MONNAIES ONT RÉUSSI À 100% !  ")
        print("==================================================")

if __name__ == '__main__':
    test_currencies_feature()
