# -*- coding: utf-8 -*-
import base64
import io
import qrcode
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class BtpDecompte(models.Model):
    _name = 'btp.decompte'
    _description = 'Décompte BTP'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'market_id, number asc, id asc'

    # --- ENTÊTE & INFORMATIONS GÉNÉRALES ---
    market_id = fields.Many2one(
        'btp.market',
        string='Marché',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        compute='_compute_partner_id',
        store=True,
        readonly=False,
        required=True,
        tracking=True,
        help="Client maître d'ouvrage (res.partner standard)"
    )
    number = fields.Integer(
        string='N° Décompte',
        required=True,
        default=1,
        tracking=True,
        help="Numéro d'ordre du décompte pour ce marché (1, 2, 3...)"
    )
    name = fields.Char(
        string='Désignation',
        compute='_compute_name',
        store=True,
        index=True
    )
    date = fields.Date(
        string='Date du décompte',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    date_attachement = fields.Date(
        string='Date d\'attachement',
        default=fields.Date.context_today,
        tracking=True,
        help="Date de l'attachement des travaux constatés"
    )
    financement = fields.Char(
        string='Financement',
        compute='_compute_financement',
        store=True,
        readonly=False,
        help="Source de financement des travaux"
    )
    invoice_ref = fields.Char(
        string='N° Facture',
        compute='_compute_invoice_ref',
        store=True,
        help="Numéro de référence de la facture"
    )
    previous_number = fields.Integer(
        string='N° Décompte Passé',
        compute='_compute_previous_number',
        store=True
    )
    qr_code_image = fields.Binary(
        string='Code QR Certification',
        compute='_compute_qr_code'
    )
    qr_code_data = fields.Text(
        string='Données Certification QR',
        compute='_compute_qr_code'
    )
    is_final = fields.Boolean(
        string='Décompte Final',
        default=False,
        tracking=True,
        help="Cocher s'il s'agit du décompte final clôturant le marché (quel que soit le N°)"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Société',
        related='market_id.company_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        compute='_compute_currency_id',
        store=True,
        readonly=False,
        tracking=True,
    )

    @api.depends('market_id.currency_id', 'company_id.currency_id')
    def _compute_currency_id(self):
        for rec in self:
            if rec.market_id and rec.market_id.currency_id:
                rec.currency_id = rec.market_id.currency_id
            elif rec.company_id and rec.company_id.currency_id:
                rec.currency_id = rec.company_id.currency_id
            else:
                fcfa = self.env['res.currency'].search([('name', '=', 'XOF'), ('active', '=', True)], limit=1)
                rec.currency_id = fcfa or self.env.company.currency_id

    def format_monetary_value(self, value):
        """Formate un montant selon les décimales de la devise (0 pour FCFA, 2 pour EUR/USD)"""
        decimals = self.currency_id.decimal_places if (self.currency_id and self.currency_id.decimal_places is not None) else 0
        fmt = f"{{:,.{decimals}f}}"
        return fmt.format(value or 0.0).replace(',', ' ')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('computed', 'Calculé'),
        ('validated', 'Validé'),
        ('invoiced', 'Facturé'),
        ('paid', 'Payé'),
        ('cancel', 'Annulé')
    ], string='État', default='draft', tracking=True, required=True)

    # --- TRAVAUX ET AVANCEMENT ---
    market_amount_untaxed = fields.Monetary(
        string='Montant HT Marché',
        related='market_id.amount_untaxed',
        store=True,
        readonly=True,
        currency_field='currency_id'
    )
    progress_rate = fields.Float(
        string='Taux d\'avancement global cumulé (%)',
        required=True,
        default=0.0,
        tracking=True,
        help="Pourcentage global CUMULÉ des travaux depuis le démarrage du chantier (ex: Décompte 1 = 25 %, Décompte 2 = 66.50 %). Ne pas saisir uniquement l'avancement du mois mais le cumul global."
    )
    cumul_travaux_ht = fields.Monetary(
        string='Travaux cumulés HT',
        compute='_compute_travaux_amounts',
        store=True,
        recursive=True,
        currency_field='currency_id',
        help="Montant HT marché * Taux d'avancement"
    )
    previous_decomptes_ht = fields.Monetary(
        string='Total décomptes précédents HT',
        compute='_compute_travaux_amounts',
        store=True,
        recursive=True,
        currency_field='currency_id',
        help="Somme des montants HT des décomptes précédents validés"
    )
    current_decompte_ht = fields.Monetary(
        string='Décompte HT actuel',
        compute='_compute_travaux_amounts',
        store=True,
        recursive=True,
        currency_field='currency_id',
        help="Montant des travaux du décompte actuel"
    )

    # --- TVA SUR DÉCOMPTE ACTUEL (18 %) ---
    tva_rate = fields.Float(
        string='Taux TVA (%)',
        default=18.0,
        readonly=True
    )
    current_decompte_tva = fields.Monetary(
        string='Montant TVA (18 %)',
        compute='_compute_tva_amounts',
        store=True,
        currency_field='currency_id',
        help="Décompte HT actuel * 18 %"
    )
    current_decompte_ttc = fields.Monetary(
        string='Montant TTC actuel',
        compute='_compute_tva_amounts',
        store=True,
        currency_field='currency_id',
        help="Décompte HT actuel + TVA"
    )

    # --- AVANCE DE DÉMARRAGE ET REMBOURSEMENT ---
    advance_rate = fields.Float(
        string='Taux Avance (%)',
        tracking=True,
        help="Taux de l'avance accordée (hérité du marché, modifiable)"
    )
    market_advance_total = fields.Monetary(
        string='Montant total Avance',
        compute='_compute_advance_amounts',
        store=True,
        currency_field='currency_id',
        help="Montant HT marché * Taux avance"
    )
    reimbursement_rate = fields.Float(
        string='Taux Remboursement (%)',
        tracking=True,
        help="Taux de remboursement de l'avance (hérité du marché, modifiable)"
    )
    current_advance_reimbursement = fields.Monetary(
        string='Remboursement avance actuel',
        compute='_compute_advance_amounts',
        store=True,
        recursive=True,
        currency_field='currency_id',
        help="Montant du remboursement de l'avance pour ce décompte"
    )
    previous_advance_reimbursed = fields.Monetary(
        string='Total avance déjà remboursée',
        compute='_compute_advance_amounts',
        store=True,
        recursive=True,
        currency_field='currency_id'
    )
    total_advance_reimbursed = fields.Monetary(
        string='Total avance remboursée cumulée',
        compute='_compute_advance_amounts',
        store=True,
        currency_field='currency_id'
    )
    remaining_advance = fields.Monetary(
        string='Solde avance restant',
        compute='_compute_advance_amounts',
        store=True,
        currency_field='currency_id'
    )

    # --- APRÈS REMBOURSEMENT ---
    ht_after_reimbursement = fields.Monetary(
        string='HT après remboursement',
        compute='_compute_after_reimbursement',
        store=True,
        currency_field='currency_id',
        help="Montant HT après déduction du remboursement de l'avance"
    )
    tva_after_reimbursement = fields.Monetary(
        string='TVA après remboursement',
        compute='_compute_after_reimbursement',
        store=True,
        currency_field='currency_id',
        help="HT après remboursement * 18 %"
    )
    ttc_after_reimbursement = fields.Monetary(
        string='TTC après remboursement',
        compute='_compute_after_reimbursement',
        store=True,
        currency_field='currency_id'
    )

    # --- RETENUES (Calculées sur le HT après remboursement K) ---
    warranty_rate = fields.Float(
        string='Taux Retenue de Garantie (%)',
        tracking=True,
        help="Taux de retenue de garantie (ex: 5 %)"
    )
    warranty_amount = fields.Monetary(
        string='Retenue de Garantie',
        compute='_compute_retentions',
        store=True,
        currency_field='currency_id',
        help="HT après remboursement * Taux garantie"
    )

    source_rate = fields.Float(
        string='Taux Retenue à la Source (%)',
        tracking=True,
        help="Taux de retenue à la source (ex: 1 %)"
    )
    source_amount = fields.Monetary(
        string='Retenue à la Source',
        compute='_compute_retentions',
        store=True,
        currency_field='currency_id',
        help="HT après remboursement * Taux source"
    )

    arcop_type = fields.Selection([
        ('rate', 'Taux (%)'),
        ('fixed', 'Montant fixe')
    ], string='Mode ARCOP', default='rate', tracking=True)
    arcop_rate = fields.Float(
        string='Taux ARCOP (%)',
        tracking=True
    )
    arcop_fixed_input = fields.Monetary(
        string='Montant ARCOP direct',
        currency_field='currency_id'
    )
    arcop_amount = fields.Monetary(
        string='Retenue ARCOP',
        compute='_compute_retentions',
        store=True,
        currency_field='currency_id'
    )

    total_retentions = fields.Monetary(
        string='Total Retenues',
        compute='_compute_retentions',
        store=True,
        currency_field='currency_id',
        help="Garantie + Retenue à la source + ARCOP"
    )

    # --- RÈGLEMENT / NET À PAYER ---
    net_to_pay = fields.Monetary(
        string='Net à Payer',
        compute='_compute_net_to_pay',
        store=True,
        currency_field='currency_id',
        help="Montant HT après déduction des retenues"
    )
    net_to_pay_words = fields.Char(
        string='Net à payer en toutes lettres',
        compute='_compute_net_to_pay_words',
        help="Montant net à payer écrit en toutes lettres"
    )
    decompte_table_html = fields.Html(
        string="Tableau Officiel du Décompte",
        compute='_compute_decompte_table_html',
        sanitize=False,
        help="Affichage en tableau officiel de tous les éléments financiers du décompte"
    )

    @api.depends('net_to_pay', 'currency_id')
    def _compute_net_to_pay_words(self):
        for rec in self:
            try:
                import num2words
                words = num2words.num2words(int(round(rec.net_to_pay or 0.0)), lang='fr')
                currency_name = rec.currency_id.currency_unit_label or rec.currency_id.name or 'Francs CFA'
                rec.net_to_pay_words = f"{words.capitalize()} ({currency_name})"
            except Exception:
                rec.net_to_pay_words = f"{rec.format_monetary_value(rec.net_to_pay)} {rec.currency_id.symbol}"

    @api.depends(
        'market_id.amount_total', 'market_id.amount_untaxed', 'progress_rate', 'cumul_travaux_ht',
        'previous_decomptes_ht', 'current_decompte_ht', 'current_decompte_tva', 'current_decompte_ttc',
        'reimbursement_rate', 'current_advance_reimbursement', 'ht_after_reimbursement',
        'tva_after_reimbursement', 'ttc_after_reimbursement', 'warranty_rate', 'warranty_amount',
        'source_rate', 'source_amount', 'total_retentions', 'net_to_pay', 'currency_id'
    )
    def _compute_decompte_table_html(self):
        for rec in self:
            curr = rec.currency_id.symbol or 'FCFA'
            rec.decompte_table_html = f"""
            <div class="table-responsive my-2">
                <table class="table table-sm table-bordered text-dark" style="border: 2px solid #000; font-size: 12.5px; width: 100%; border-collapse: collapse; margin-bottom: 0px;">
                    <thead>
                        <tr style="background-color: #f2f2f2; border: 1px solid #000;">
                            <th style="border: 1px solid #000; padding: 5px 8px; width: 66%; font-weight: bold; text-transform: uppercase;">DÉSIGNATION DES ÉLÉMENTS DU DÉCOMPTE</th>
                            <th style="border: 1px solid #000; padding: 5px 8px; width: 12%; text-align: center; font-weight: bold; text-transform: uppercase;">RÉF / TAUX</th>
                            <th style="border: 1px solid #000; padding: 5px 8px; width: 22%; text-align: right; background-color: #9ab7d9; font-weight: bold;">EN {curr}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px; font-weight: bold;">MONTANT TOTAL DU MARCHÉ TOUTES TAXES COMPRISES (TTC)</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">A</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right; font-weight: bold;">{rec.format_monetary_value(rec.market_id.amount_total)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px; font-weight: bold;">MONTANT TOTAL DU MARCHÉ HORS TAXES (HT)</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">B</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right; font-weight: bold;">{rec.format_monetary_value(rec.market_id.amount_untaxed)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">TAUX D'AVANCEMENT GLOBAL DES TRAVAUX</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">C</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right; font-weight: bold;">{rec.progress_rate:.2f} %</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">MONTANT CUMULÉ DES TRAVAUX RÉALISÉS HORS TAXES</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">D</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right;">{rec.format_monetary_value(rec.cumul_travaux_ht)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">MONTANT HORS TAXES DES DÉCOMPTES ANTÉRIEURS N°{rec.previous_number}</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">E</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right;">{rec.format_monetary_value(rec.previous_decomptes_ht)}</td>
                        </tr>
                        <tr style="border: 1px solid #000; background-color: #eaf1f8; font-weight: bold;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">MONTANT HORS TAXES DU DÉCOMPTE N°{rec.number:02d}</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center;">F</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right; color: #0d6efd;">{rec.format_monetary_value(rec.current_decompte_ht)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">TVA SUR LE DÉCOMPTE N°{rec.number:02d} (18 %)</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">G</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right;">{rec.format_monetary_value(rec.current_decompte_tva)}</td>
                        </tr>
                        <tr style="border: 1px solid #000; background-color: #f2f2f2; font-weight: bold;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">MONTANT TTC DU DÉCOMPTE N°{rec.number:02d}</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center;">H</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right;">{rec.format_monetary_value(rec.current_decompte_ttc)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">TAUX DE REMBOURSEMENT DE L'AVANCE DE DÉMARRAGE</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">I</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right; font-weight: bold;">{rec.reimbursement_rate:.0f} %</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">REMBOURSEMENT DE L'AVANCE DE DÉMARRAGE (HT)</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">J</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right; color: #dc3545;">- {rec.format_monetary_value(rec.current_advance_reimbursement)}</td>
                        </tr>
                        <tr style="border: 1px solid #000; background-color: #eaf1f8; font-weight: bold;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">MONTANT HT DU DÉCOMPTE APRÈS REMBOURSEMENT DE L'AVANCE</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center;">K</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right;">{rec.format_monetary_value(rec.ht_after_reimbursement)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">TVA APRÈS REMBOURSEMENT DE L'AVANCE (18 %)</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">L</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right;">{rec.format_monetary_value(rec.tva_after_reimbursement)}</td>
                        </tr>
                        <tr style="border: 1px solid #000; background-color: #f2f2f2; font-weight: bold;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">MONTANT TTC DU DÉCOMPTE APRÈS REMBOURSEMENT</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center;">M</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right;">{rec.format_monetary_value(rec.ttc_after_reimbursement)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">RETENUE DE GARANTIE ({rec.warranty_rate:.1f} %)</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">N</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right;">{rec.format_monetary_value(rec.warranty_amount)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">RETENUE À LA SOURCE ({rec.source_rate:.1f} %)</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center; font-weight: bold;">O</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right;">{rec.format_monetary_value(rec.source_amount)}</td>
                        </tr>
                        <tr style="border: 1px solid #000; color: #dc3545; font-weight: bold;">
                            <td style="border: 1px solid #000; padding: 4px 8px;">TOTAL DES RETENUES LÉGALES ET CONTRACTUELLES</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: center;">P</td>
                            <td style="border: 1px solid #000; padding: 4px 8px; text-align: right;">{rec.format_monetary_value(rec.total_retentions)}</td>
                        </tr>
                        <tr style="border: 2px solid #000; background-color: #9ab7d9; font-weight: bold; font-size: 13.5px;">
                            <td style="border: 2px solid #000; padding: 6px 8px; text-transform: uppercase;">MONTANT NET À PAYER DU DÉCOMPTE N°{rec.number:02d}</td>
                            <td style="border: 2px solid #000; padding: 6px 8px; text-align: center; font-size: 15px;">Q ★</td>
                            <td style="border: 2px solid #000; padding: 6px 8px; text-align: right; color: #000; font-weight: bold;">{rec.format_monetary_value(rec.net_to_pay)} {curr}</td>
                        </tr>
                    </tbody>
                </table>
                <div class="p-2 mt-2 bg-light border text-dark" style="border: 1px solid #000 !important;">
                    <strong>Arrêté le présent décompte à la somme nette de :</strong>
                    <span class="text-uppercase fw-bold">{rec.net_to_pay_words or ''}</span>
                </div>
            </div>
            """

    # --- FACTURATION ODOO STANDARD (account.move) ---
    move_id = fields.Many2one(
        'account.move',
        string='Facture Odoo',
        readonly=True,
        copy=False,
        ondelete='set null',
        tracking=True,
        help="Facture client standard Odoo créée à partir de ce décompte"
    )
    payment_state = fields.Selection(
        related='move_id.payment_state',
        string='État de paiement facture',
        readonly=True,
        store=True
    )

    _sql_constraints = [
        ('market_number_uniq', 'unique(market_id, number)', 'Ce numéro de décompte existe déjà pour ce marché !'),
    ]

    # --- ONCHANGE / INITIALISATION ---
    @api.onchange('market_id')
    def _onchange_market_id(self):
        if self.market_id:
            self.partner_id = self.market_id.partner_id
            self.advance_rate = self.market_id.advance_rate
            self.reimbursement_rate = self.market_id.reimbursement_rate
            self.warranty_rate = self.market_id.warranty_rate
            self.source_rate = self.market_id.source_rate
            self.arcop_type = self.market_id.arcop_type
            self.arcop_rate = self.market_id.arcop_rate
            self.arcop_fixed_input = self.market_id.arcop_fixed_amount

            # Auto-numérotation : N° suivant et pré-remplissage du taux d'avancement cumulé
            valid_decomptes = self.market_id.decompte_ids.filtered(lambda d: d.id != self._origin.id and d.state in ('validated', 'invoiced', 'paid'))
            if valid_decomptes:
                last = valid_decomptes.sorted(key=lambda d: d.number)[-1]
                self.number = max(self.market_id.decompte_ids.mapped('number') or [0]) + 1
                if not self.progress_rate or self.progress_rate < last.progress_rate:
                    self.progress_rate = last.progress_rate
            else:
                existing_numbers = self.market_id.decompte_ids.mapped('number')
                self.number = (max(existing_numbers) + 1) if existing_numbers else 1

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('market_id'):
                market = self.env['btp.market'].browse(vals['market_id'])
                if market.is_final_done:
                    raise ValidationError(_("Le décompte final de ce marché a déjà été validé. Aucun nouveau décompte ne peut être créé."))
                if not vals.get('partner_id'):
                    vals['partner_id'] = market.partner_id.id
                if 'advance_rate' not in vals:
                    vals['advance_rate'] = market.advance_rate
                if 'reimbursement_rate' not in vals:
                    vals['reimbursement_rate'] = market.reimbursement_rate
                if 'warranty_rate' not in vals:
                    vals['warranty_rate'] = market.warranty_rate
                if 'source_rate' not in vals:
                    vals['source_rate'] = market.source_rate
                if 'arcop_type' not in vals:
                    vals['arcop_type'] = market.arcop_type
                if 'arcop_rate' not in vals:
                    vals['arcop_rate'] = market.arcop_rate
                if 'arcop_fixed_input' not in vals:
                    vals['arcop_fixed_input'] = market.arcop_fixed_amount
                if 'number' not in vals:
                    existing = market.decompte_ids.mapped('number')
                    vals['number'] = (max(existing) + 1) if existing else 1
        return super().create(vals_list)

    @api.depends('market_id', 'market_id.partner_id')
    def _compute_partner_id(self):
        for rec in self:
            if rec.market_id and not rec.partner_id:
                rec.partner_id = rec.market_id.partner_id

    @api.depends('market_id', 'number', 'is_final')
    def _compute_name(self):
        for rec in self:
            if rec.market_id and rec.number:
                final_str = " FINAL" if rec.is_final else ""
                rec.name = f"Décompte N°{rec.number}{final_str} - {rec.market_id.name}"
            else:
                rec.name = _("Nouveau Décompte")

    @api.depends('market_id', 'market_id.financement')
    def _compute_financement(self):
        for rec in self:
            if rec.market_id and rec.market_id.financement:
                rec.financement = rec.market_id.financement
            elif not rec.financement:
                rec.financement = 'Fonds propres'

    @api.depends('move_id', 'move_id.name', 'number')
    def _compute_invoice_ref(self):
        for rec in self:
            if rec.move_id and rec.move_id.name and rec.move_id.name != '/':
                rec.invoice_ref = rec.move_id.name
            else:
                rec.invoice_ref = f"FACT-{rec.number:04d}" if rec.number else "FACT-0001"

    @api.depends('number')
    def _compute_previous_number(self):
        for rec in self:
            rec.previous_number = max(0, (rec.number or 1) - 1)

    @api.depends('invoice_ref', 'number', 'current_decompte_ht', 'current_decompte_tva', 'net_to_pay', 'partner_id', 'company_id', 'company_id.name', 'company_id.ifu', 'company_id.rccm', 'company_id.ati')
    def _compute_qr_code(self):
        for rec in self:
            try:
                comp = rec.company_id
                ifu = getattr(comp, 'ifu', '') or comp.vat or '00045678W'
                rccm = getattr(comp, 'rccm', '') or comp.company_registry or 'BF-OUA-01-2025-B12-00456'
                ati = getattr(comp, 'ati', '') or 'ATI-BTP-2025/112'
                inv_ref = rec.invoice_ref or f"FACT-{rec.number:04d}"

                qr_payload = (
                    f"ENTREPRISE: {comp.name}\n"
                    f"PAYS: {comp.country_id.name or 'Burkina Faso'}\n"
                    f"IFU: {ifu}\n"
                    f"RCCM: {rccm}\n"
                    f"ATI: {ati}\n"
                    f"FACTURE: {inv_ref}\n"
                    f"DECOMPTE: N°{rec.number:02d}\n"
                    f"CLIENT: {rec.partner_id.name or ''}\n"
                    f"MARCHE: {rec.market_id.name or ''}\n"
                    f"MONTANT_HT: {rec.current_decompte_ht:,.0f} {rec.currency_id.symbol}\n"
                    f"TVA_18: {rec.current_decompte_tva:,.0f} {rec.currency_id.symbol}\n"
                    f"NET_A_PAYER: {rec.net_to_pay:,.0f} {rec.currency_id.symbol}\n"
                    f"CERTIFICATION_E_SINTAX: VALID-{rec.id:06d}"
                )
                rec.qr_code_data = qr_payload

                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=4,
                    border=1,
                )
                qr.add_data(qr_payload)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                rec.qr_code_image = base64.b64encode(buffer.getvalue())
            except Exception:
                rec.qr_code_data = False
                rec.qr_code_image = False

    # --- CALCULS TRAVAUX ET AVANCEMENT ---
    @api.depends(
        'market_amount_untaxed', 'progress_rate', 'market_id', 'number',
        'market_id.decompte_ids.state', 'market_id.decompte_ids.current_decompte_ht'
    )
    def _compute_travaux_amounts(self):
        for rec in self:
            cumul = (rec.market_amount_untaxed * rec.progress_rate) / 100.0
            rec.cumul_travaux_ht = rec.currency_id.round(cumul) if rec.currency_id else round(cumul, 2)

            # Somme des décomptes précédents validés
            prev_decomptes = rec.market_id.decompte_ids.filtered(
                lambda d: d.id != rec.id and d.number < rec.number and d.state in ('validated', 'invoiced', 'paid')
            )
            prev_sum = sum(prev_decomptes.mapped('current_decompte_ht'))
            rec.previous_decomptes_ht = prev_sum

            # Décompte HT actuel = Travaux cumulés - Décomptes précédents (garanti >= 0)
            diff = rec.cumul_travaux_ht - rec.previous_decomptes_ht
            rec.current_decompte_ht = max(0.0, diff)

    @api.depends('current_decompte_ht', 'tva_rate')
    def _compute_tva_amounts(self):
        for rec in self:
            tva = (rec.current_decompte_ht * rec.tva_rate) / 100.0
            rec.current_decompte_tva = rec.currency_id.round(tva) if rec.currency_id else round(tva, 2)
            rec.current_decompte_ttc = rec.current_decompte_ht + rec.current_decompte_tva

    # --- CALCULS AVANCE & REMBOURSEMENT ---
    @api.depends(
        'market_amount_untaxed', 'advance_rate', 'reimbursement_rate',
        'market_id', 'number', 'market_id.decompte_ids.state',
        'market_id.decompte_ids.current_advance_reimbursement',
        'current_decompte_ht'
    )
    def _compute_advance_amounts(self):
        for rec in self:
            advance_tot = (rec.market_amount_untaxed * rec.advance_rate) / 100.0
            rec.market_advance_total = rec.currency_id.round(advance_tot) if rec.currency_id else round(advance_tot, 2)

            # Précédents remboursements validés
            prev_decomptes = rec.market_id.decompte_ids.filtered(
                lambda d: d.id != rec.id and d.number < rec.number and d.state in ('validated', 'invoiced', 'paid')
            )
            prev_reimbursed = sum(prev_decomptes.mapped('current_advance_reimbursement'))
            rec.previous_advance_reimbursed = prev_reimbursed

            # Calcul théorique du remboursement : Montant HT marché * Taux avance * Taux remboursement
            cur_reimbursement = rec.market_amount_untaxed * (rec.advance_rate / 100.0) * (rec.reimbursement_rate / 100.0)
            cur_reimbursement = rec.currency_id.round(cur_reimbursement) if rec.currency_id else round(cur_reimbursement, 2)

            # Plafond 1 : ne peut dépasser l'avance restante
            remaining_before = max(0.0, rec.market_advance_total - prev_reimbursed)
            # Plafond 2 : ne peut pas excéder le montant HT des travaux du décompte actuel (évite tout montant négatif)
            max_deductible = max(0.0, rec.current_decompte_ht)
            cur_reimbursement = min(cur_reimbursement, remaining_before, max_deductible)
            rec.current_advance_reimbursement = cur_reimbursement

            rec.total_advance_reimbursed = prev_reimbursed + cur_reimbursement
            rec.remaining_advance = max(0.0, rec.market_advance_total - rec.total_advance_reimbursed)

    # --- CALCULS APRÈS REMBOURSEMENT ---
    @api.depends('current_decompte_ht', 'current_advance_reimbursement', 'tva_rate')
    def _compute_after_reimbursement(self):
        for rec in self:
            # HT après remboursement = Décompte HT actuel - Remboursement d'avance (garanti >= 0)
            k_val = max(0.0, rec.current_decompte_ht - rec.current_advance_reimbursement)
            rec.ht_after_reimbursement = k_val

            tva_k = (k_val * rec.tva_rate) / 100.0
            rec.tva_after_reimbursement = rec.currency_id.round(tva_k) if rec.currency_id else round(tva_k, 2)
            rec.ttc_after_reimbursement = rec.ht_after_reimbursement + rec.tva_after_reimbursement

    # --- CALCULS DES RETENUES (Calculées sur le HT après remboursement) ---
    @api.depends(
        'ht_after_reimbursement', 'warranty_rate', 'source_rate',
        'arcop_type', 'arcop_rate', 'arcop_fixed_input'
    )
    def _compute_retentions(self):
        for rec in self:
            base_k = max(0.0, rec.ht_after_reimbursement)

            # Retenue de garantie
            w_amt = (base_k * rec.warranty_rate) / 100.0
            rec.warranty_amount = rec.currency_id.round(w_amt) if rec.currency_id else round(w_amt, 2)

            # Retenue à la source
            s_amt = (base_k * rec.source_rate) / 100.0
            rec.source_amount = rec.currency_id.round(s_amt) if rec.currency_id else round(s_amt, 2)

            # Retenue ARCOP
            if rec.arcop_type == 'rate':
                a_amt = (base_k * rec.arcop_rate) / 100.0
                rec.arcop_amount = rec.currency_id.round(a_amt) if rec.currency_id else round(a_amt, 2)
            else:
                rec.arcop_amount = rec.arcop_fixed_input or 0.0

            rec.total_retentions = rec.warranty_amount + rec.source_amount + rec.arcop_amount

    # --- NET À PAYER ---
    @api.depends('ht_after_reimbursement', 'total_retentions')
    def _compute_net_to_pay(self):
        for rec in self:
            # Net à payer = HT après remboursement - Total retenues (garanti >= 0)
            net = max(0.0, rec.ht_after_reimbursement - rec.total_retentions)
            rec.net_to_pay = rec.currency_id.round(net) if rec.currency_id else round(net, 2)

    # --- VALIDATIONS ET CONTRAINTES ---
    @api.constrains('market_id', 'progress_rate', 'number', 'state', 'current_advance_reimbursement')
    def _check_business_rules(self):
        for rec in self:
            if not rec.market_id:
                raise ValidationError(_("Un décompte doit obligatoirement être rattaché à un marché."))

            if rec.number <= 0:
                raise ValidationError(_("Le numéro de décompte doit être un entier strictement positif."))

            if rec.progress_rate < 0 or rec.progress_rate > 100:
                raise ValidationError(_("Le taux d'avancement doit être compris entre 0 et 100 % (Actuel : %s %%)") % rec.progress_rate)

            if rec.cumul_travaux_ht > rec.market_amount_untaxed:
                raise ValidationError(_("Le montant cumulé des travaux (%s) ne peut pas excéder le montant HT du marché (%s).") % (rec.cumul_travaux_ht, rec.market_amount_untaxed))

            if rec.net_to_pay < 0:
                raise ValidationError(_("Le net à payer ne peut pas être négatif (%s). Veuillez vérifier les déductions et retenues.") % rec.net_to_pay)

            # Vérification de non-régression de l'avancement par rapport au décompte précédent validé
            prev_decomptes = rec.market_id.decompte_ids.filtered(
                lambda d: d.id != rec.id and d.number < rec.number and d.state in ('validated', 'invoiced', 'paid')
            )
            if prev_decomptes:
                last_prev = prev_decomptes.sorted(key=lambda d: d.number)[-1]
                if rec.progress_rate < last_prev.progress_rate:
                    raise ValidationError(
                        _("L'avancement saisi (%s %%) ne peut pas être inférieur à celui du décompte précédent N°%s (%s %%).")
                        % (rec.progress_rate, last_prev.number, last_prev.progress_rate)
                    )

            # Vérification du décompte final
            if rec.market_id:
                # 1. Pas plus d'un décompte final validé par marché
                if rec.is_final:
                    other_finals = rec.market_id.decompte_ids.filtered(
                        lambda d: d.id != rec.id and d.is_final and d.state in ('validated', 'invoiced', 'paid')
                    )
                    if other_finals:
                        raise ValidationError(
                            _("Un décompte final (N°%s) a déjà été validé pour ce marché.") % other_finals[0].number
                        )
                # 2. Aucun décompte avec un numéro postérieur au décompte final
                validated_finals = rec.market_id.decompte_ids.filtered(
                    lambda d: d.id != rec.id and d.is_final and d.state in ('validated', 'invoiced', 'paid')
                )
                if validated_finals and rec.number > validated_finals[0].number:
                    raise ValidationError(
                        _("Le décompte final (N°%s) de ce marché a déjà été validé. Aucun décompte postérieur (N°%s) ne peut être créé ou validé.")
                        % (validated_finals[0].number, rec.number)
                    )

    # --- ACTIONS DE FLUX DU DÉCOMPTE ---
    def action_compute(self):
        for rec in self:
            rec._compute_travaux_amounts()
            rec._compute_tva_amounts()
            rec._compute_advance_amounts()
            rec._compute_after_reimbursement()
            rec._compute_retentions()
            rec._compute_net_to_pay()
            if rec.state == 'draft':
                rec.state = 'computed'

    def action_validate(self):
        for rec in self:
            rec.action_compute()
            rec.write({'state': 'validated'})
            # Si le décompte est final, clôturer le marché
            if rec.is_final:
                rec.market_id.write({'state': 'done'})
            elif rec.market_id.state == 'draft':
                rec.market_id.write({'state': 'in_progress'})

    def action_reset_draft(self):
        for rec in self:
            if rec.move_id and rec.move_id.state != 'cancel':
                raise UserError(_("Impossible de remettre en brouillon un décompte ayant une facture active. Annulez d'abord la facture %s.") % rec.move_id.name)
            rec.write({'state': 'draft'})

    def action_cancel(self):
        for rec in self:
            if rec.move_id and rec.move_id.state != 'cancel':
                raise UserError(_("Impossible d'annuler un décompte ayant une facture active. Annulez d'abord la facture %s.") % rec.move_id.name)
            rec.write({'state': 'cancel'})

    # --- CRÉATION DE LA FACTURE ODOO STANDARD (account.move) ---
    def action_create_invoice(self):
        self.ensure_one()
        if self.state not in ('validated', 'computed'):
            raise UserError(_("Le décompte doit être validé avant de pouvoir générer une facture."))

        if self.move_id and self.move_id.state != 'cancel':
            raise UserError(_("Une facture Odoo (%s) existe déjà pour ce décompte.") % self.move_id.name)

        # Rechercher ou créer une taxe à 18 % pour la facture
        Tax = self.env['account.tax']
        tax_18 = Tax.search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 18.0),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        tax_ids = [(4, tax_18.id)] if tax_18 else []

        invoice_lines = []

        # 1. Ligne principale : Travaux du décompte actuel
        invoice_lines.append((0, 0, {
            'name': _("Travaux Décompte N°%s - Marché : %s\nObjet : %s\nAvancement global : %s %%") % (
                self.number, self.market_id.name, self.market_id.objet or '', self.progress_rate
            ),
            'quantity': 1.0,
            'price_unit': self.current_decompte_ht,
            'tax_ids': tax_ids,
        }))

        # 2. Ligne déduction : Remboursement de l'avance
        if self.current_advance_reimbursement > 0:
            invoice_lines.append((0, 0, {
                'name': _("Déduction remboursement avance de démarrage (%s %%)") % self.reimbursement_rate,
                'quantity': 1.0,
                'price_unit': -self.current_advance_reimbursement,
                'tax_ids': tax_ids,
            }))

        # Note d'information sur les retenues dans la facture
        narration_parts = [
            _("DÉCOMPTE BTP N°%s%s") % (self.number, " (FINAL)" if self.is_final else ""),
            _("Marché : %s") % self.market_id.name,
            _("Objet : %s") % (self.market_id.objet or ""),
            "--------------------------------------------------",
            _("Travaux cumulés HT : %s %s") % (f"{self.cumul_travaux_ht:,.2f}", self.currency_id.symbol),
            _("Décomptes antérieurs HT : %s %s") % (f"{self.previous_decomptes_ht:,.2f}", self.currency_id.symbol),
            _("Décompte actuel HT : %s %s") % (f"{self.current_decompte_ht:,.2f}", self.currency_id.symbol),
            _("Remboursement avance : -%s %s") % (f"{self.current_advance_reimbursement:,.2f}", self.currency_id.symbol),
            _("HT après remboursement : %s %s") % (f"{self.ht_after_reimbursement:,.2f}", self.currency_id.symbol),
            "--------------------------------------------------",
            _("RETENUES APPLIQUÉES :"),
            _("- Retenue de garantie (%s %%) : %s %s") % (self.warranty_rate, f"{self.warranty_amount:,.2f}", self.currency_id.symbol),
            _("- Retenue à la source (%s %%) : %s %s") % (self.source_rate, f"{self.source_amount:,.2f}", self.currency_id.symbol),
            _("- Retenue ARCOP : %s %s") % (f"{self.arcop_amount:,.2f}", self.currency_id.symbol),
            _("Total des retenues : %s %s") % (f"{self.total_retentions:,.2f}", self.currency_id.symbol),
            "--------------------------------------------------",
            _("NET À PAYER : %s %s") % (f"{self.net_to_pay:,.2f}", self.currency_id.symbol),
        ]

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.date,
            'date': self.date,
            'ref': f"Décompte N°{self.number} - {self.market_id.name}",
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_line_ids': invoice_lines,
            'narration': "\n".join(narration_parts),
            'decompte_id': self.id,
        }

        move = self.env['account.move'].create(invoice_vals)
        self.write({
            'move_id': move.id,
            'state': 'invoiced'
        })

        return {
            'name': _('Facture Décompte'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',
        }

    def action_view_invoice(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_("Aucune facture n'est rattachée à ce décompte."))
        return {
            'name': _('Facture Décompte'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
            'target': 'current',
        }
