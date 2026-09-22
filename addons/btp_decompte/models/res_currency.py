# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    sequence = fields.Integer(string='Séquence', default=100)
    _order = 'sequence, name'

    _rec_names_search = ['name', 'symbol', 'full_name', 'currency_unit_label']

    @api.depends('name', 'symbol')
    def _compute_display_name(self):
        for rec in self:
            if rec.name in ('XOF', 'XAF'):
                rec.display_name = f"FCFA ({rec.name})"
            elif rec.symbol and rec.symbol != rec.name:
                rec.display_name = f"{rec.name} ({rec.symbol})"
            else:
                rec.display_name = rec.name
