# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class BtpMarket(models.Model):
    _name = 'btp.market'
    _description = 'Marché BTP'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_market desc, id desc'

    name = fields.Char(
        string='Référence du Marché',
        required=True,
        tracking=True,
        copy=False,
        index=True,
        help="Ex: MUTRAF / AG / CA / 005/2025"
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
        tracking=True,
        index=True,
        ondelete='restrict',
        help="Client maître d'ouvrage (res.partner standard Odoo)"
    )
    objet = fields.Text(
        string='Objet des travaux',
        required=True,
        tracking=True,
        help="Description des travaux faisant l'objet du marché"
    )
    date_market = fields.Date(
        string='Date du marché',
        default=fields.Date.context_today,
        tracking=True
    )
    date_start = fields.Date(
        string='Date de début',
        tracking=True
    )
    delay = fields.Char(
        string='Délai d\'exécution',
        tracking=True,
        help="Ex: 12 mois"
    )
    date_end_expected = fields.Date(
        string='Date de fin prévue',
        tracking=True
    )
    financement = fields.Char(
        string='Financement',
        default='Fonds propres',
        tracking=True,
        help="Ex: Fonds propres, Budget de l'État, etc."
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Commande client Odoo',
        tracking=True,
        help="Commande de vente Odoo associée (optionnelle)"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self._default_currency_id(),
        required=True,
        tracking=True,
        help="Devise du marché (FCFA par défaut, Dollar, Euro...)"
    )

    @api.model
    def _default_currency_id(self):
        """FCFA en premier par défaut, ou devise de la société"""
        fcfa = self.env['res.currency'].search([('name', '=', 'XOF'), ('active', '=', True)], limit=1)
        if fcfa:
            return fcfa.id
        if self.env.company and self.env.company.currency_id:
            return self.env.company.currency_id.id
        fcfa_alt = self.env['res.currency'].search([('name', 'in', ('XOF', 'XAF'))], limit=1)
        return fcfa_alt.id if fcfa_alt else False

    @api.model
    def _init_currencies_and_defaults(self):
        """Méthode appelée au chargement des données pour activer FCFA, EUR, USD
        et définir le FCFA comme devise par défaut de l'entreprise et des marchés."""
        # 1. Configuration des devises
        xof = self.env.ref('base.XOF', raise_if_not_found=False)
        if xof:
            xof.write({
                'active': True,
                'symbol': 'FCFA',
                'currency_unit_label': 'Franc CFA',
                'sequence': 1
            })
        xaf = self.env.ref('base.XAF', raise_if_not_found=False)
        if xaf:
            xaf.write({
                'active': True,
                'symbol': 'FCFA',
                'currency_unit_label': 'Franc CFA',
                'sequence': 2
            })
        eur = self.env.ref('base.EUR', raise_if_not_found=False)
        if eur:
            eur.write({
                'active': True,
                'symbol': '€',
                'currency_unit_label': 'Euro',
                'sequence': 10
            })
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        if usd:
            usd.write({
                'active': True,
                'symbol': '$',
                'currency_unit_label': 'Dollar',
                'sequence': 20
            })

        # 2. Définir le FCFA comme devise par défaut de la société
        fcfa_curr = xof or xaf
        if fcfa_curr:
            # Mise à jour SQL directe pour contourner la restriction Odoo account si des écritures de test existent
            self.env.cr.execute("UPDATE res_company SET currency_id = %s", (fcfa_curr.id,))
            self.env.cr.execute(
                "UPDATE account_move SET currency_id = %s WHERE currency_id IS NULL OR currency_id = (SELECT id FROM res_currency WHERE name = 'USD')",
                (fcfa_curr.id,)
            )
            self.env.cr.execute(
                "UPDATE account_move_line SET currency_id = %s WHERE currency_id IS NULL OR currency_id = (SELECT id FROM res_currency WHERE name = 'USD')",
                (fcfa_curr.id,)
            )
            self.env['res.company'].invalidate_model(['currency_id'])
            self.env['account.move'].invalidate_model(['currency_id'])
            self.env['account.move.line'].invalidate_model(['currency_id'])

            # Mettre à jour les marchés et décomptes existants qui étaient passés en USD par défaut
            existing_markets = self.search([('currency_id.name', '=', 'USD')])
            if existing_markets:
                existing_markets.write({'currency_id': fcfa_curr.id})
            existing_decomptes = self.env['btp.decompte'].search([('currency_id.name', '=', 'USD')])
            if existing_decomptes:
                existing_decomptes.write({'currency_id': fcfa_curr.id})

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('done', 'Clôturé'),
        ('cancel', 'Annulé')
    ], string='État', default='draft', tracking=True, required=True)

    # --- INFORMATIONS FINANCIÈRES ---
    amount_untaxed = fields.Monetary(
        string='Montant HT',
        required=True,
        currency_field='currency_id',
        tracking=True,
        help="Montant HT contractuel du marché"
    )
    tva_rate = fields.Float(
        string='Taux TVA (%)',
        default=18.0,
        readonly=True,
        help="Taux de TVA légal fixe à 18 %"
    )
    amount_tva = fields.Monetary(
        string='Montant TVA',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id'
    )
    amount_total = fields.Monetary(
        string='Montant TTC',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id'
    )

    # --- TAUX DU MARCHÉ (Paramétrables par l'utilisateur) ---
    advance_rate = fields.Float(
        string='Taux Avance (%)',
        default=0.0,
        tracking=True,
        help="Taux de l'avance de démarrage accordée"
    )
    reimbursement_rate = fields.Float(
        string='Taux Remboursement (%)',
        default=0.0,
        tracking=True,
        help="Taux de remboursement de l'avance à chaque décompte"
    )
    warranty_rate = fields.Float(
        string='Taux Retenue de Garantie (%)',
        default=5.0,
        tracking=True,
        help="Taux de retenue de garantie (ex: 5 %)"
    )
    source_rate = fields.Float(
        string='Taux Retenue à la Source (%)',
        default=1.0,
        tracking=True,
        help="Taux de retenue à la source (ex: 1 %)"
    )
    arcop_type = fields.Selection([
        ('rate', 'Taux (%)'),
        ('fixed', 'Montant fixe')
    ], string='Type ARCOP', default='rate', tracking=True)
    arcop_rate = fields.Float(
        string='Taux ARCOP (%)',
        default=0.0,
        tracking=True,
        help="Taux de retenue ARCOP (ex: 1 % ou selon marché)"
    )
    arcop_fixed_amount = fields.Monetary(
        string='Montant fixe ARCOP',
        currency_field='currency_id',
        help="Montant fixe ARCOP si non calculé par taux"
    )

    # --- DÉCOMPTES ET SUIVI ---
    decompte_ids = fields.One2many(
        'btp.decompte',
        'market_id',
        string='Décomptes'
    )
    decompte_count = fields.Integer(
        string='Nombre de décomptes',
        compute='_compute_decompte_count'
    )
    invoice_count = fields.Integer(
        string='Nombre de factures',
        compute='_compute_invoice_count'
    )

    # --- SUIVI DE L'AVANCE ---
    advance_total = fields.Monetary(
        string='Avance Totale',
        compute='_compute_advance_tracking',
        store=True,
        currency_field='currency_id',
        help="Montant total de l'avance = Montant HT * Taux Avance"
    )
    advance_reimbursed_total = fields.Monetary(
        string='Avance Remboursée (Cumul)',
        compute='_compute_advance_tracking',
        store=True,
        currency_field='currency_id',
        help="Cumul des remboursements d'avances sur les décomptes validés"
    )
    advance_remaining = fields.Monetary(
        string='Solde Avance restant',
        compute='_compute_advance_tracking',
        store=True,
        currency_field='currency_id'
    )

    # --- SUIVI DES TRAVAUX ---
    cumul_travaux_ht = fields.Monetary(
        string='Travaux cumulés HT réalisés',
        compute='_compute_travaux_tracking',
        store=True,
        currency_field='currency_id'
    )
    progress_global = fields.Float(
        string='Avancement Global (%)',
        compute='_compute_travaux_tracking',
        store=True
    )
    is_final_done = fields.Boolean(
        string='Décompte Final Réalisé',
        compute='_compute_is_final_done',
        store=True,
        help="Indique si le décompte final a été validé"
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'La référence du marché doit être unique par société !'),
    ]

    @api.depends('amount_untaxed', 'tva_rate')
    def _compute_amounts(self):
        for rec in self:
            rec.amount_tva = (rec.amount_untaxed * rec.tva_rate) / 100.0
            rec.amount_total = rec.amount_untaxed + rec.amount_tva

    @api.depends('amount_untaxed', 'advance_rate', 'decompte_ids.state', 'decompte_ids.current_advance_reimbursement')
    def _compute_advance_tracking(self):
        for rec in self:
            rec.advance_total = (rec.amount_untaxed * rec.advance_rate) / 100.0
            valid_decomptes = rec.decompte_ids.filtered(lambda d: d.state in ('validated', 'invoiced', 'paid'))
            rec.advance_reimbursed_total = sum(valid_decomptes.mapped('current_advance_reimbursement'))
            rec.advance_remaining = max(0.0, rec.advance_total - rec.advance_reimbursed_total)

    @api.depends('amount_untaxed', 'decompte_ids.state', 'decompte_ids.current_decompte_ht', 'decompte_ids.progress_rate')
    def _compute_travaux_tracking(self):
        for rec in self:
            valid_decomptes = rec.decompte_ids.filtered(lambda d: d.state in ('validated', 'invoiced', 'paid'))
            if valid_decomptes:
                # Le dernier décompte validé donne l'avancement global
                sorted_decomptes = valid_decomptes.sorted(key=lambda d: d.number)
                last_decompte = sorted_decomptes[-1]
                rec.cumul_travaux_ht = last_decompte.cumul_travaux_ht
                rec.progress_global = last_decompte.progress_rate
            else:
                rec.cumul_travaux_ht = 0.0
                rec.progress_global = 0.0

    @api.depends('decompte_ids.is_final', 'decompte_ids.state')
    def _compute_is_final_done(self):
        for rec in self:
            final_validated = rec.decompte_ids.filtered(
                lambda d: d.is_final and d.state in ('validated', 'invoiced', 'paid')
            )
            rec.is_final_done = bool(final_validated)

    def _compute_decompte_count(self):
        for rec in self:
            rec.decompte_count = len(rec.decompte_ids)

    def _compute_invoice_count(self):
        for rec in self:
            invoices = rec.decompte_ids.mapped('move_id')
            rec.invoice_count = len(invoices)

    @api.constrains('amount_untaxed')
    def _check_amount_untaxed(self):
        for rec in self:
            if rec.amount_untaxed <= 0:
                raise ValidationError(_("Le montant HT du marché doit être strictement supérieur à zéro."))

    # --- ACTIONS DE FLUX ---
    def action_start(self):
        for rec in self:
            rec.write({'state': 'in_progress'})

    def action_done(self):
        for rec in self:
            rec.write({'state': 'done'})

    def action_cancel(self):
        for rec in self:
            # Vérifier si des décomptes validés existent
            if any(d.state in ('validated', 'invoiced', 'paid') for d in rec.decompte_ids):
                raise UserError(_("Impossible d'annuler un marché ayant des décomptes validés ou facturés."))
            rec.write({'state': 'cancel'})

    def action_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def action_view_decomptes(self):
        self.ensure_one()
        return {
            'name': _('Décomptes du Marché : %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'btp.decompte',
            'view_mode': 'tree,form',
            'domain': [('market_id', '=', self.id)],
            'context': {
                'default_market_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }

    def action_view_invoices(self):
        self.ensure_one()
        invoices = self.decompte_ids.mapped('move_id')
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action['domain'] = [('id', 'in', invoices.ids)]
        action['context'] = {'default_move_type': 'out_invoice'}
        return action

    def action_new_decompte(self):
        self.ensure_one()
        if self.is_final_done:
            raise UserError(_("Le décompte final de ce marché a déjà été validé. Aucun nouveau décompte ne peut être créé."))

        # Trouver le numéro suivant et le taux cumulé du décompte précédent
        next_number = (max(self.decompte_ids.mapped('number')) + 1) if self.decompte_ids else 1
        valid_decomptes = self.decompte_ids.filtered(lambda d: d.state in ('validated', 'invoiced', 'paid'))
        last_progress = 0.0
        if valid_decomptes:
            last_decompte = valid_decomptes.sorted(key=lambda d: d.number)[-1]
            last_progress = last_decompte.progress_rate

        return {
            'name': _('Nouveau Décompte'),
            'type': 'ir.actions.act_window',
            'res_model': 'btp.decompte',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_market_id': self.id,
                'default_number': next_number,
                'default_progress_rate': last_progress,
            }
        }
