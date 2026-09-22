# -*- coding: utf-8 -*-
{
    'name': 'Gestion des Décomptes BTP',
    'version': '17.0.1.0.0',
    'category': 'Construction/BTP',
    'summary': 'Gestion des marchés, décomptes successifs, avances, retenues et facturation BTP',
    'description': """
Module métier BTP pour Odoo 17 :
================================
- Gestion des marchés de travaux (référence, client, montant HT, TVA 18%, délai, etc.)
- Gestion des décomptes successifs d'avancement
- Calcul des montants cumulés et du décompte actuel
- Gestion des avances de démarrage et du remboursement de l'avance
- Calcul officiel du montant HT après remboursement de l'avance et TVA 18%
- Retenues personnalisables : retenue de garantie, retenue à la source, ARCOP
- Calcul automatique du net à payer
- Prise en charge du décompte final et clôture du marché
- Intégration native avec Odoo Facturation (account.move)
- Galerie visuelle des modèles de factures avec volet gauche illustré
- Modèle de facture spécifique bordereau de travaux avec déduction et TVA 18%
- Intégration avec les Ventes (sale.order) et Contacts (res.partner)
- Rapport PDF professionnel de décompte BTP
- Configuration complète de l'entreprise (Logo, Nom, Email, IFU, RCCM, ATI, Régime fiscal, Division fiscale)
    """,
    'author': 'Antigravity / BTP Solutions',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'sale_management',
        'account',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/res_currency_data.xml',
        'data/btp_facture_modele_data.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/btp_petit_marche_views.xml',
        'views/btp_market_views.xml',
        'views/btp_decompte_views.xml',
        'views/btp_facture_modele_views.xml',
        'views/account_move_views.xml',
        'views/account_move_honoraires_views.xml',
        'views/account_move_etudes_views.xml',
        'views/account_move_decompte_views.xml',
        'views/menus.xml',
        'report/btp_decompte_report.xml',
        'report/btp_decompte_template.xml',
        'report/btp_petit_marche_report.xml',
        'report/btp_petit_marche_template.xml',
        'report/btp_facture_bordereau_report.xml',
        'report/btp_facture_bordereau_template.xml',
        'report/btp_facture_honoraires_report.xml',
        'report/btp_facture_honoraires_template.xml',
        'report/btp_facture_etudes_report.xml',
        'report/btp_facture_etudes_template.xml',
        'report/btp_facture_decompte_report.xml',
        'report/btp_facture_decompte_template.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
