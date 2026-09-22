# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    ifu = fields.Char(
        string='N° IFU',
        default='00045678W',
        help="Numéro d'Identifiant Fiscal Unique (IFU)"
    )
    rccm = fields.Char(
        string='N° RCCM',
        default='BF-OUA-01-2025-B12-00456',
        help="Registre du Commerce et du Crédit Mobilier (RCCM)"
    )
    ati = fields.Char(
        string='N° ATI',
        default='ATI-BTP-2025/112',
        help="Agrément Technique / Autorisation d'Exercer BTP"
    )
    regime_fiscal = fields.Char(
        string='Régime fiscal',
        default="Réel Normal d'Imposition (RNI)",
        help="Ex: Réel Normal d'Imposition (RNI), Réel Simplifié d'Imposition (RSI)"
    )
    division_fiscale = fields.Char(
        string='Division fiscale',
        default="Direction des Grandes Entreprises (DGE)",
        help="Ex: Direction des Grandes Entreprises (DGE), Centre des Impôts"
    )

    @api.model
    def default_get(self, fields_list):
        res = super(ResCompany, self).default_get(fields_list)
        if 'currency_id' in fields_list or not res.get('currency_id'):
            fcfa = self.env['res.currency'].search([('name', '=', 'XOF'), ('active', '=', True)], limit=1)
            if fcfa:
                res['currency_id'] = fcfa.id
        return res

    def write(self, vals):
        if 'currency_id' in vals:
            new_curr_id = vals.get('currency_id')
            for company in self:
                if new_curr_id and company.currency_id.id != new_curr_id:
                    self.env.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (new_curr_id, company.id))
                    self.env.cr.execute(
                        "UPDATE account_move SET currency_id = %s WHERE company_id = %s AND currency_id = %s",
                        (new_curr_id, company.id, company.currency_id.id)
                    )
                    self.env.cr.execute(
                        "UPDATE account_move_line SET currency_id = %s WHERE company_id = %s AND (currency_id = %s OR currency_id IS NULL)",
                        (new_curr_id, company.id, company.currency_id.id)
                    )
            self.invalidate_model(['currency_id'])
            vals = dict(vals)
            vals.pop('currency_id')
        return super().write(vals)

    @api.model
    def action_open_my_company(self):
        """Action pratique ouvrant directement la fiche de la société de l'utilisateur pour modification"""
        company = self.env.company
        return {
            'name': _("Configuration de l'Entreprise"),
            'type': 'ir.actions.act_window',
            'res_model': 'res.company',
            'view_mode': 'form',
            'res_id': company.id,
            'target': 'current',
        }
