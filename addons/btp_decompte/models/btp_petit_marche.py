# -*- coding: utf-8 -*-
import base64
import io
import qrcode
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class BtpPetitMarche(models.Model):
    _name = 'btp.petit.marche'
    _description = 'Petit Marché BTP (Sans Décompte)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    # --- INFORMATIONS GÉNÉRALES ---
    name = fields.Char(
        string='Référence du Marché',
        required=True,
        tracking=True,
        copy=False,
        index=True,
        help="Référence officielle du petit marché (ex: PM-2025/001)"
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
        string='Objet du Marché',
        required=True,
        tracking=True,
        help="Description des travaux faisant l'objet du petit marché"
    )
    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    invoice_ref = fields.Char(
        string='N° Facture',
        compute='_compute_invoice_ref',
        store=True,
        help="Numéro de référence de la facture"
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
        help="Devise du marché (FCFA par défaut, Euro, Dollar...)"
    )

    qr_code_image = fields.Binary(
        string='Code QR Certification',
        compute='_compute_qr_code'
    )
    qr_code_data = fields.Text(
        string='Données Certification QR',
        compute='_compute_qr_code'
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

    def format_monetary_value(self, value):
        """Formate un montant selon les décimales de la devise (0 pour FCFA, 2 pour EUR/USD)"""
        decimals = self.currency_id.decimal_places if (self.currency_id and self.currency_id.decimal_places is not None) else 0
        fmt = f"{{:,.{decimals}f}}"
        return fmt.format(value or 0.0).replace(',', ' ')

    @api.depends('move_id', 'move_id.name', 'name')
    def _compute_invoice_ref(self):
        for rec in self:
            if rec.move_id and rec.move_id.name and rec.move_id.name != '/':
                rec.invoice_ref = rec.move_id.name
            else:
                rec.invoice_ref = f"FACT-AVANCE-{rec.name}" if rec.name else "FACT-AVANCE"

    @api.depends('invoice_ref', 'name', 'amount_untaxed', 'advance_amount_untaxed', 'advance_tva', 'amount_to_pay', 'partner_id', 'company_id')
    def _compute_qr_code(self):
        for rec in self:
            try:
                comp = rec.company_id
                ifu = getattr(comp, 'ifu', '') or comp.vat or '00045678W'
                rccm = getattr(comp, 'rccm', '') or comp.company_registry or 'BF-OUA-01-2025-B12-00456'
                ati = getattr(comp, 'ati', '') or 'ATI-BTP-2025/112'
                inv_ref = rec.invoice_ref or f"FACT-{rec.name}"

                qr_payload = (
                    f"ENTREPRISE: {comp.name}\n"
                    f"PAYS: {comp.country_id.name or 'Burkina Faso'}\n"
                    f"IFU: {ifu}\n"
                    f"RCCM: {rccm}\n"
                    f"ATI: {ati}\n"
                    f"FACTURE: {inv_ref}\n"
                    f"PETIT_MARCHE: {rec.name}\n"
                    f"CLIENT: {rec.partner_id.name or ''}\n"
                    f"OBJET: {rec.objet or ''}\n"
                    f"MONTANT_TTC: {rec.amount_total:,.0f} {rec.currency_id.symbol}\n"
                    f"MONTANT_HT: {rec.amount_untaxed:,.0f} {rec.currency_id.symbol}\n"
                    f"AVANCE_HT: {rec.advance_amount_untaxed:,.0f} {rec.currency_id.symbol}\n"
                    f"TVA_18: {rec.advance_tva:,.0f} {rec.currency_id.symbol}\n"
                    f"NET_A_PAYER: {rec.amount_to_pay:,.0f} {rec.currency_id.symbol}\n"
                    f"CERTIFICATION_E_SINTAX: VALID-PM-{rec.id:06d}"
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

    # --- MONTANTS DU MARCHÉ ---
    amount_untaxed = fields.Monetary(
        string='Montant HT',
        required=True,
        tracking=True,
        currency_field='currency_id',
        help="Montant total hors taxes du petit marché"
    )
    tva_rate = fields.Float(
        string='Taux TVA (%)',
        default=18.0,
        readonly=True,
        help="Taux de TVA légal fixe à 18 %"
    )
    amount_tva = fields.Monetary(
        string='Montant TVA (18 %)',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
        help="Montant HT * 18 %"
    )
    amount_total = fields.Monetary(
        string='Montant TTC',
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
        help="Montant HT + TVA"
    )

    # --- AVANCE ET MONTANT À PAYER ---
    advance_rate = fields.Float(
        string='Taux d\'avance (%)',
        required=True,
        default=0.0,
        tracking=True,
        help="Taux d'avance accordé, saisi manuellement et modifiable (ex: 50 %)"
    )
    advance_amount_untaxed = fields.Monetary(
        string='Avance HT',
        compute='_compute_advance_amounts',
        store=True,
        currency_field='currency_id',
        help="Montant HT du marché * Taux d'avance / 100"
    )
    advance_tva = fields.Monetary(
        string='TVA sur l\'avance (18 %)',
        compute='_compute_advance_amounts',
        store=True,
        currency_field='currency_id',
        help="Avance HT * 18 %"
    )
    amount_to_pay = fields.Monetary(
        string='Montant total à payer',
        compute='_compute_advance_amounts',
        store=True,
        currency_field='currency_id',
        help="Avance HT + TVA sur l'avance"
    )
    amount_to_pay_words = fields.Char(
        string='Montant en toutes lettres',
        compute='_compute_amount_words',
        help="Montant total de l'avance à payer écrit en toutes lettres"
    )

    financial_table_html = fields.Html(
        string="Tableau Récapitulatif des Éléments",
        compute='_compute_financial_table_html',
        sanitize=False,
        help="Affichage en tableau structuré de tous les éléments financiers du petit marché"
    )

    @api.depends('amount_to_pay', 'currency_id')
    def _compute_amount_words(self):
        for rec in self:
            try:
                import num2words
                words = num2words.num2words(int(round(rec.amount_to_pay or 0.0)), lang='fr')
                currency_name = rec.currency_id.currency_unit_label or rec.currency_id.name or 'Francs CFA'
                rec.amount_to_pay_words = f"{words.capitalize()} ({currency_name})"
            except Exception:
                rec.amount_to_pay_words = f"{rec.format_monetary_value(rec.amount_to_pay)} {rec.currency_id.symbol}"

    @api.depends('amount_total', 'amount_untaxed', 'amount_tva', 'advance_rate', 'advance_amount_untaxed', 'advance_tva', 'amount_to_pay', 'currency_id')
    def _compute_financial_table_html(self):
        for rec in self:
            curr = rec.currency_id.symbol or 'FCFA'
            rec.financial_table_html = f"""
            <div class="table-responsive my-2">
                <table class="table table-sm table-bordered text-dark" style="border: 2px solid #000; font-size: 13px; width: 100%; border-collapse: collapse; margin-bottom: 0px;">
                    <thead>
                        <tr style="background-color: #f2f2f2; border: 1px solid #000;">
                            <th style="border: 1px solid #000; padding: 6px 10px; width: 62%; font-weight: bold; text-transform: uppercase;">DÉSIGNATION DES ÉLÉMENTS DU MARCHÉ</th>
                            <th style="border: 1px solid #000; padding: 6px 10px; width: 18%; text-align: center; font-weight: bold; text-transform: uppercase;">TAUX / RÉF</th>
                            <th style="border: 1px solid #000; padding: 6px 10px; width: 20%; text-align: right; background-color: #9ab7d9; font-weight: bold;">EN {curr}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px; font-weight: bold;">1. MONTANT TOTAL DU MARCHÉ TOUTES TAXES COMPRISES (TTC)</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: center;">-</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: right; font-weight: bold;">{rec.format_monetary_value(rec.amount_total)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px; font-weight: bold;">2. MONTANT TOTAL DU MARCHÉ HORS TAXES (HT)</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: center;">-</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: right; font-weight: bold;">{rec.format_monetary_value(rec.amount_untaxed)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">3. TVA LÉGALE SUR LE MARCHÉ (18 %)</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: center; font-weight: bold;">18.00 %</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: right;">{rec.format_monetary_value(rec.amount_tva)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">4. TAUX DE L'AVANCE ACCORDÉE</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: center; font-weight: bold;">{rec.advance_rate:.2f} %</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: center; font-weight: bold;">-</td>
                        </tr>
                        <tr style="border: 1px solid #000; background-color: #eaf1f8;">
                            <td style="border: 1px solid #000; padding: 6px 10px; font-weight: bold;">5. MONTANT DE L'AVANCE DEMANDÉE HORS TAXES (HT)</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: center;">{rec.advance_rate:.0f} %</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: right; font-weight: bold; color: #0d6efd;">{rec.format_monetary_value(rec.advance_amount_untaxed)}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">6. TVA SUR L'AVANCE (18 %)</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: center; font-weight: bold;">18.00 %</td>
                            <td style="border: 1px solid #000; padding: 6px 10px; text-align: right;">{rec.format_monetary_value(rec.advance_tva)}</td>
                        </tr>
                        <tr style="border: 2px solid #000; background-color: #9ab7d9; font-weight: bold; font-size: 14px;">
                            <td style="border: 2px solid #000; padding: 8px 10px; text-transform: uppercase;">7. MONTANT TOTAL DE L'AVANCE À PAYER (TTC)</td>
                            <td style="border: 2px solid #000; padding: 8px 10px; text-align: center; font-size: 15px;">★</td>
                            <td style="border: 2px solid #000; padding: 8px 10px; text-align: right; color: #000; font-weight: bold;">{rec.format_monetary_value(rec.amount_to_pay)} {curr}</td>
                        </tr>
                    </tbody>
                </table>
                <div class="p-2 mt-2 bg-light border text-dark" style="border: 1px solid #000 !important;">
                    <strong>Arrêtée la présente facture d'avance à la somme de :</strong>
                    <span class="text-uppercase fw-bold">{rec.amount_to_pay_words or ''}</span>
                </div>
            </div>
            """

    # --- FACTURATION & STATUT ---
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('computed', 'Calculé'),
        ('validated', 'Validé'),
        ('invoiced', 'Facturé'),
        ('paid', 'Payé'),
        ('cancel', 'Annulé'),
    ], string='Statut', default='draft', tracking=True, required=True)

    move_id = fields.Many2one(
        'account.move',
        string='Facture Odoo',
        readonly=True,
        copy=False,
        tracking=True,
        help="Facture client standard Odoo créée à partir de ce petit marché"
    )
    payment_state = fields.Selection(
        related='move_id.payment_state',
        string='État de paiement facture',
        readonly=True,
        store=True
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'La référence de ce petit marché existe déjà pour cette société !'),
    ]

    # --- CALCULS DES MONTANTS ---
    @api.onchange('amount_total')
    def _onchange_amount_total(self):
        if self.amount_total and not self.amount_untaxed:
            rate = 1.0 + ((self.tva_rate or 18.0) / 100.0)
            self.amount_untaxed = round(self.amount_total / rate)

    @api.depends('amount_untaxed', 'tva_rate')
    def _compute_amounts(self):
        for rec in self:
            tva = (rec.amount_untaxed * (rec.tva_rate or 18.0)) / 100.0
            rec.amount_tva = rec.currency_id.round(tva) if rec.currency_id else round(tva, 2)
            rec.amount_total = rec.amount_untaxed + rec.amount_tva

    @api.depends('amount_untaxed', 'advance_rate', 'tva_rate')
    def _compute_advance_amounts(self):
        for rec in self:
            # Avance HT = Montant HT * Taux d'avance / 100
            adv_ht = (rec.amount_untaxed * (rec.advance_rate or 0.0)) / 100.0
            rec.advance_amount_untaxed = rec.currency_id.round(adv_ht) if rec.currency_id else round(adv_ht, 2)

            # TVA sur l'avance = Avance HT * 18 / 100
            adv_tva = (rec.advance_amount_untaxed * (rec.tva_rate or 18.0)) / 100.0
            rec.advance_tva = rec.currency_id.round(adv_tva) if rec.currency_id else round(adv_tva, 2)

            # Montant total à payer = Avance HT + TVA sur l'avance
            rec.amount_to_pay = rec.advance_amount_untaxed + rec.advance_tva

    # --- CONTRAINTES MÉTIER ---
    @api.constrains('advance_rate', 'amount_untaxed')
    def _check_rates_and_amounts(self):
        for rec in self:
            if rec.amount_untaxed < 0:
                raise ValidationError(_("Le montant HT du marché ne peut pas être négatif."))
            if rec.advance_rate < 0 or rec.advance_rate > 100:
                raise ValidationError(_("Le taux d'avance doit être compris entre 0 et 100 % (Actuel : %s %%)") % rec.advance_rate)

    # --- ACTIONS DU WORKFLOW ---
    def action_compute(self):
        for rec in self:
            rec._compute_amounts()
            rec._compute_advance_amounts()
            if rec.state == 'draft':
                rec.state = 'computed'

    def action_validate(self):
        for rec in self:
            rec.action_compute()
            if not rec.partner_id:
                raise ValidationError(_("Veuillez sélectionner un client avant de valider le marché."))
            if rec.amount_untaxed <= 0:
                raise ValidationError(_("Le montant HT du marché doit être supérieur à zéro."))
            rec.write({'state': 'validated'})

    def action_create_invoice(self):
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError(_("Impossible de créer une facture sans client."))
        if self.move_id:
            raise UserError(_("Une facture Odoo existe déjà pour ce petit marché (%s).") % self.move_id.name)
        if self.advance_amount_untaxed <= 0:
            raise UserError(_("Le montant de l'avance HT doit être strictement supérieur à zéro pour pouvoir générer une facture."))

        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not journal:
            raise UserError(_("Aucun journal des ventes n'a été trouvé pour la société %s.") % self.company_id.name)

        # Taxe TVA 18 %
        tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 18.0),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not tax:
            tax = self.env['account.tax'].search([
                ('type_tax_use', '=', 'sale'),
                ('amount', '=', 18.0)
            ], limit=1)
        if not tax:
            tax = self.env['account.tax'].create({
                'name': 'TVA 18%',
                'amount': 18.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'company_id': self.company_id.id,
            })

        line_name = f"Avance ({self.advance_rate:.0f} %) - Petit Marché : {self.name}\nObjet : {self.objet}"

        narration_text = (
            f"FACTURE D'AVANCE - PETIT MARCHÉ BTP\n"
            f"============================================================\n"
            f"Client                    : {self.partner_id.name}\n"
            f"Référence du marché       : {self.name}\n"
            f"Objet des travaux         : {self.objet}\n"
            f"Date                      : {self.date}\n"
            f"------------------------------------------------------------\n"
            f"TABLEAU RÉCAPITULATIF DES ÉLÉMENTS DU MARCHÉ :\n"
            f"1. Montant total TTC      : {self.format_monetary_value(self.amount_total)} {self.currency_id.symbol}\n"
            f"2. Montant total HT       : {self.format_monetary_value(self.amount_untaxed)} {self.currency_id.symbol}\n"
            f"3. TVA légale (18 %)      : {self.format_monetary_value(self.amount_tva)} {self.currency_id.symbol}\n"
            f"4. Taux d'avance accordé  : {self.advance_rate:.2f} %\n"
            f"5. Avance demandée (HT)   : {self.format_monetary_value(self.advance_amount_untaxed)} {self.currency_id.symbol}\n"
            f"6. TVA sur l'avance (18%) : {self.format_monetary_value(self.advance_tva)} {self.currency_id.symbol}\n"
            f"------------------------------------------------------------\n"
            f"7. MONTANT TOTAL À PAYER  : {self.format_monetary_value(self.amount_to_pay)} {self.currency_id.symbol}\n"
            f"============================================================\n"
            f"Arrêtée à la somme de : {self.amount_to_pay_words}\n"
        )

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'journal_id': journal.id,
            'invoice_date': self.date or fields.Date.context_today(self),
            'ref': f"AVANCE-{self.name}",
            'narration': narration_text,
            'petit_marche_id': self.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': line_name,
                    'quantity': 1.0,
                    'price_unit': self.advance_amount_untaxed,
                    'tax_ids': [(6, 0, [tax.id])],
                })
            ],
        }

        move = self.env['account.move'].create(invoice_vals)
        self.write({
            'move_id': move.id,
            'state': 'invoiced',
        })
        return self.action_view_invoice()

    def action_view_invoice(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_("Aucune facture Odoo n'est rattachée à ce petit marché."))
        return {
            'name': _('Facture du Petit Marché : %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref('btp_decompte.action_report_btp_petit_marche').report_action(self)

    def action_draft(self):
        for rec in self:
            if rec.move_id and rec.move_id.state == 'posted':
                raise UserError(_("Impossible de repasser en brouillon un petit marché dont la facture est déjà comptabilisée."))
            rec.write({'state': 'draft'})

    def action_cancel(self):
        for rec in self:
            if rec.move_id and rec.move_id.state == 'posted':
                raise UserError(_("Impossible d'annuler un petit marché dont la facture est déjà comptabilisée."))
            rec.write({'state': 'cancel'})
