# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    btp_ifu = fields.Char(
        related='company_id.ifu',
        readonly=False,
        string="N° IFU",
        help="Identifiant Fiscal Unique affiché sur la facture BTP"
    )
    btp_rccm = fields.Char(
        related='company_id.rccm',
        readonly=False,
        string="N° RCCM",
        help="Numéro RCCM affiché sur la facture BTP"
    )
    btp_ati = fields.Char(
        related='company_id.ati',
        readonly=False,
        string="N° ATI",
        help="Agrément Technique / ATI BTP"
    )
    btp_regime_fiscal = fields.Char(
        related='company_id.regime_fiscal',
        readonly=False,
        string="Régime fiscal",
        help="Ex: Réel Normal d'Imposition (RNI)"
    )
    btp_division_fiscale = fields.Char(
        related='company_id.division_fiscale',
        readonly=False,
        string="Division fiscale",
        help="Ex: Direction des Grandes Entreprises (DGE)"
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=False,
        string="Devise Principale",
        help="Devise principale de l'entreprise (FCFA par défaut, Dollar, Euro...)"
    )

