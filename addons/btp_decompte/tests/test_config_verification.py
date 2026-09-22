# -*- coding: utf-8 -*-
import odoo

def verify_btp_configuration():
    odoo.tools.config.parse_config(['-r', 'odoo', '-w', 'odoo', '--db_host', 'db', '--db_port', '5432', '-d', 'facturation_electronique'])
    registry = odoo.registry('facturation_electronique')
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        
        print("=== 1. TEST FORMULAIRE RES.COMPANY ===")
        comp_views = env['res.company'].get_views([(False, 'form')])
        form_arch = comp_views['views']['form']['arch']
        fields_to_check = ['ifu', 'rccm', 'ati', 'regime_fiscal', 'division_fiscale']
        for f in fields_to_check:
            assert f'name="{f}"' in form_arch, f"Field {f} missing from res.company form view"
            print(f"  [OK] Champ {f} présent dans la vue formulaire Société")
        
        print("\n=== 2. TEST PARAMÈTRES RES.CONFIG.SETTINGS ===")
        settings_views = env['res.config.settings'].get_views([(False, 'form')])
        settings_arch = settings_views['views']['form']['arch']
        for f in ['btp_ifu', 'btp_rccm', 'btp_ati', 'btp_regime_fiscal', 'btp_division_fiscale']:
            assert f'name="{f}"' in settings_arch, f"Field {f} missing from settings arch"
            print(f"  [OK] Paramètre {f} présent dans la vue Paramètres BTP")
            
        print("\n=== 3. TEST ACTIONS ET MENUS BTP CONFIGURATION ===")
        menu_company = env.ref('btp_decompte.menu_btp_my_company')
        menu_settings = env.ref('btp_decompte.menu_btp_settings')
        print(f"  [OK] Menu Entreprise: {menu_company.complete_name} -> {menu_company.action.name}")
        print(f"  [OK] Menu Paramètres: {menu_settings.complete_name} -> {menu_settings.action.name}")

        print("\n=== 4. TEST MODIFICATION DONNÉES ENTREPRISE ET DÉCOMPTE ===")
        comp = env.company
        test_data = {
            'name': 'ENTREPRISE BTP DEMO & SERVICES SARL',
            'email': 'contact@btp-demo-services.com',
            'ifu': '00099887Z',
            'rccm': 'BF-OUA-01-2026-B14-09988',
            'ati': 'ATI-BTP-2026/A-001',
            'regime_fiscal': "Réel Normal d'Imposition (RNI)",
            'division_fiscale': "Direction des Grandes Entreprises (DGE)"
        }
        comp.write(test_data)
        cr.commit()
        print("  [OK] Écriture des données entreprise réussie :")
        for k, v in test_data.items():
            print(f"       - {k}: {getattr(comp, k)}")

        print("\n=== 5. TEST GÉNÉRATION DU DÉCOMPTE & QR CODE DYNAMIQUE ===")
        decompte = env['btp.decompte'].search([], limit=1)
        if decompte:
            decompte._compute_qr_code()
            print("  [OK] Payload QR code recalculé :")
            for line in decompte.qr_code_data.split('\n')[:7]:
                print(f"       {line}")
                
            report = env['ir.actions.report']
            pdf_content, _ = report._render_qweb_pdf('btp_decompte.action_report_btp_decompte', decompte.ids)
            print(f"  [OK] Rapport PDF de décompte / facture généré ({len(pdf_content)} octets)")

        print("\n>>> TOUS LES TESTS DE CONFIGURATION ONT RÉUSSI AVEC SUCCÈS ! <<<")

if __name__ == '__main__':
    verify_btp_configuration()
