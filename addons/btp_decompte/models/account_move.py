# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import models, fields, api, _
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    # --- SÉLECTION DU MODÈLE DE FACTURE (GALERIE AVEC VOLET GAUCHE) ---
    facture_modele_id = fields.Many2one(
        'btp.facture.modele',
        string='Modèle de Facture',
        tracking=True,
        default=lambda self: self._default_facture_modele_id(),
        help="Choisissez le modèle visuel de facture souhaité parmi les modèles disponibles."
    )
    facture_modele_code = fields.Char(
        related='facture_modele_id.code',
        string='Code Modèle',
        store=True,
        readonly=True
    )
    facture_modele_image = fields.Binary(
        related='facture_modele_id.image_preview',
        string='Aperçu Visuel du Modèle',
        readonly=True
    )

    @api.model
    def _default_facture_modele_id(self):
        mod = self.env['btp.facture.modele'].search([('code', '=', 'bordereau_travaux')], limit=1)
        if not mod:
            mod = self.env['btp.facture.modele'].search([('is_default', '=', True)], limit=1)
        return mod.id if mod else False

    @api.onchange('facture_modele_id')
    def _onchange_facture_modele_id(self):
        if self.facture_modele_id:
            if self.facture_modele_id.city_default:
                self.facture_city = self.facture_modele_id.city_default
            if self.facture_modele_id.deduction_label_default:
                self.facture_deduction_label = self.facture_modele_id.deduction_label_default
            if self.facture_modele_id.deduction_rate_default:
                self.facture_deduction_rate = self.facture_modele_id.deduction_rate_default
            if self.facture_modele_id.signatory_default:
                self.facture_signatory = self.facture_modele_id.signatory_default
            if self.facture_modele_id.code == 'petit_marche':
                self.btp_market_type = 'petit'
            elif self.facture_modele_id.code == 'grand_marche':
                self.btp_market_type = 'grand'


    # --- PERSONNALISATION DE LA FACTURE SPÉCIFIQUE (NOUVEAU MODÈLE BORDEREAU) ---
    facture_city = fields.Char(
        string='Ville de signature',
        default='Ouagadougou',
        tracking=True,
        help="Ville affichée en en-tête (ex: Ouagadougou le...)"
    )
    facture_objet = fields.Text(
        string='Objet des travaux / prestation',
        tracking=True,
        help="Objet affiché sur la facture sous le 'Doit :'"
    )
    facture_deduction_label = fields.Char(
        string='Libellé déduction facture perçue',
        default='Montant de la facture n°1 perçue de 50%',
        tracking=True
    )
    facture_deduction_rate = fields.Float(
        string='Taux de déduction (%)',
        default=50.0,
        tracking=True
    )
    facture_marche_ht = fields.Monetary(
        string='Montant HT du Marché',
        currency_field='currency_id',
        tracking=True,
        default=0.0,
        help="Montant contractuel total HT du marché"
    )
    facture_amount_presente_ht = fields.Monetary(
        string='Montant Principal (Présente Facture HTVA)',
        currency_field='currency_id',
        tracking=True,
        default=0.0,
        readonly=False,
        help="Saisissez ici le montant principal : tous les calculs (déduction 50%, Net HT, TVA 18%, Net TTC, en lettres) s'exécutent automatiquement !"
    )
    facture_deduction_amount = fields.Monetary(
        string='Montant de la facture perçue déduit',
        compute='_compute_facture_bordereau_totals',
        inverse='_inverse_facture_deduction_amount',
        store=True,
        readonly=False,
        currency_field='currency_id'
    )
    facture_net_ht = fields.Monetary(
        string='MONTANT NET DE LA PRESENTE FACTURE EN HTVA',
        compute='_compute_facture_bordereau_totals',
        store=True,
        currency_field='currency_id'
    )
    facture_tva_rate = fields.Float(
        string='Taux de TVA (%)',
        default=18.0,
        tracking=True,
        help="Taux de TVA en pourcentage (défaut 18%)"
    )
    facture_tva_18 = fields.Monetary(
        string='Montant de la TVA 18%',
        compute='_compute_facture_bordereau_totals',
        store=True,
        currency_field='currency_id'
    )
    facture_net_ttc = fields.Monetary(
        string='MONTANT NET DE LA PRESENTE FACTURE EN TTC',
        compute='_compute_facture_bordereau_totals',
        store=True,
        currency_field='currency_id'
    )
    facture_net_ttc_words = fields.Char(
        string='Arrêtée en toutes lettres',
        compute='_compute_facture_bordereau_words',
        store=True
    )
    facture_signatory = fields.Char(
        string='Intitulé Signataire',
        default='Signataire',
        tracking=True
    )
    facture_bordereau_preview_html = fields.Html(
        string='Aperçu Tableau Bordereau',
        compute='_compute_facture_bordereau_html',
        sanitize=False
    )
    qr_code_image = fields.Binary(
        string='QR Code Certification',
        compute='_compute_qr_code',
        store=False,
        help="QR Code officiel de certification de la facture"
    )

    def _compute_qr_code(self):
        for rec in self:
            try:
                import qrcode
                import io
                import base64
                ifu = rec.company_id.ifu or rec.company_id.vat or ''
                client_ifu = getattr(rec.partner_id, 'ifu', False) or rec.partner_id.vat or ''
                qr_text = (
                    f"FACTURE:{rec.name or rec.ref or ''}\n"
                    f"DATE:{rec.invoice_date or fields.Date.today()}\n"
                    f"EMETTEUR:{rec.company_id.name} (IFU:{ifu})\n"
                    f"CLIENT:{rec.partner_id.name} (IFU:{client_ifu})\n"
                    f"NET_TTC:{rec.facture_net_ttc or rec.amount_total} {rec.currency_id.name or 'XOF'}"
                )
                qr = qrcode.QRCode(version=1, box_size=3, border=2)
                qr.add_data(qr_text)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = io.BytesIO()
                # pyrefly: ignore [unexpected-keyword]
                img.save(buffer, format="PNG")
                rec.qr_code_image = base64.b64encode(buffer.getvalue())
            except Exception:
                rec.qr_code_image = False

    # --- CATÉGORIE MARCHÉ BTP (EXISTANT PRÉSERVÉ) ---
    btp_market_type = fields.Selection([
        ('none', 'Standard (Non BTP)'),
        ('petit', 'Petit Marché BTP (Sans décompte)'),
        ('grand', 'Grand Marché BTP (Avec décomptes)'),
    ], string='Catégorie Marché BTP', compute='_compute_btp_market_type', store=True, readonly=False, tracking=True)

    decompte_id = fields.Many2one(
        'btp.decompte',
        string='Décompte BTP',
        copy=False,
        help="Décompte BTP à l'origine de cette facture"
    )
    market_id = fields.Many2one(
        'btp.market',
        string='Marché BTP',
        related='decompte_id.market_id',
        store=True,
        readonly=True,
        help="Marché BTP associé"
    )
    petit_marche_id = fields.Many2one(
        'btp.petit.marche',
        string='Petit Marché BTP',
        copy=False,
        help="Petit marché BTP à l'origine de cette facture d'avance"
    )

    @api.depends('petit_marche_id', 'decompte_id')
    def _compute_btp_market_type(self):
        for rec in self:
            if rec.petit_marche_id:
                rec.btp_market_type = 'petit'
            elif rec.decompte_id:
                rec.btp_market_type = 'grand'
            elif not rec.btp_market_type:
                rec.btp_market_type = 'none'

    # Champs relatifs Petit Marché
    petit_marche_amount_untaxed = fields.Monetary(related='petit_marche_id.amount_untaxed', string='Montant HT Petit Marché', readonly=True)
    petit_marche_amount_tva = fields.Monetary(related='petit_marche_id.amount_tva', string='TVA Marché (18 %)', readonly=True)
    petit_marche_amount_total = fields.Monetary(related='petit_marche_id.amount_total', string='Montant TTC Petit Marché', readonly=True)
    petit_marche_advance_rate = fields.Float(related='petit_marche_id.advance_rate', string='Taux Avance (%)', readonly=True)
    petit_marche_advance_untaxed = fields.Monetary(related='petit_marche_id.advance_amount_untaxed', string='Avance HT', readonly=True)
    petit_marche_advance_tva = fields.Monetary(related='petit_marche_id.advance_tva', string='TVA sur Avance (18 %)', readonly=True)
    petit_marche_amount_to_pay = fields.Monetary(related='petit_marche_id.amount_to_pay', string='Total à Payer', readonly=True)
    petit_marche_financial_table_html = fields.Html(related='petit_marche_id.financial_table_html', string='Tableau Récapitulatif Petit Marché', readonly=True, sanitize=False)

    # Champs relatifs Grand Marché (Décompte)
    decompte_number = fields.Integer(related='decompte_id.number', string='N° Décompte', readonly=True)
    decompte_progress_rate = fields.Float(related='decompte_id.progress_rate', string='Taux Avancement (%)', readonly=True)
    decompte_cumul_travaux_ht = fields.Monetary(related='decompte_id.cumul_travaux_ht', string='Travaux Cumulés HT', readonly=True)
    decompte_current_ht = fields.Monetary(related='decompte_id.current_decompte_ht', string='Décompte Actuel HT', readonly=True)
    decompte_advance_reimbursed = fields.Monetary(related='decompte_id.current_advance_reimbursement', string='Remboursement Avance', readonly=True)
    decompte_ht_after_reimbursement = fields.Monetary(related='decompte_id.ht_after_reimbursement', string='HT après Remboursement', readonly=True)
    decompte_total_retentions = fields.Monetary(related='decompte_id.total_retentions', string='Total Retenues', readonly=True)
    decompte_net_to_pay = fields.Monetary(related='decompte_id.net_to_pay', string='Net à Payer Décompte', readonly=True)
    decompte_table_html = fields.Html(related='decompte_id.decompte_table_html', string='Tableau Officiel Décompte', readonly=True, sanitize=False)

    # --- CALCULS FINANCIERS DU MODÈLE BORDEREAU DE TRAVAUX ---
    @api.onchange('facture_amount_presente_ht', 'facture_marche_ht', 'facture_deduction_rate', 'facture_tva_rate', 'facture_objet')
    def _onchange_facture_amount_presente_ht(self):
        for move in self:
            move._sync_facture_bordereau_calculations()

    @api.onchange('facture_deduction_amount')
    def _onchange_facture_deduction_amount(self):
        for move in self:
            presente = move.facture_amount_presente_ht or move.facture_marche_ht or 0.0
            if move.facture_deduction_amount:
                # La déduction est toujours négative (avec un signe moins)
                move.facture_deduction_amount = - abs(move.facture_deduction_amount)
                if presente > 0:
                    move.facture_deduction_rate = round((abs(move.facture_deduction_amount) / presente) * 100.0, 2)
            ded_abs = abs(move.facture_deduction_amount or 0.0)
            net_ht = max(0.0, presente - ded_abs)
            move.facture_net_ht = move.currency_id.round(net_ht) if move.currency_id else round(net_ht, 2)
            tva_rate = move.facture_tva_rate if move.facture_tva_rate is not False else 18.0
            tva = (move.facture_net_ht * tva_rate) / 100.0
            move.facture_tva_18 = move.currency_id.round(tva) if move.currency_id else round(tva, 2)
            move.facture_net_ttc = move.facture_net_ht + move.facture_tva_18
            move._compute_facture_bordereau_words()
            move._compute_facture_bordereau_html()

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids_btp_bordereau(self):
        for move in self:
            lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
            if lines:
                total_lines = sum(l.price_subtotal if l.price_subtotal else (l.quantity * l.price_unit) for l in lines)
                if total_lines > 0:
                    move.facture_amount_presente_ht = total_lines
                    if not move.facture_marche_ht:
                        move.facture_marche_ht = total_lines
                    move._sync_facture_bordereau_calculations()

    def _sync_facture_bordereau_calculations(self):
        for move in self:
            lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
            lines_sum = sum(l.price_subtotal if l.price_subtotal else (l.quantity * l.price_unit) for l in lines) if lines else 0.0

            # 1. Remplissage automatique intelligent & synchronisation bidirectionnelle :
            if move.facture_marche_ht and not move.facture_amount_presente_ht:
                move.facture_amount_presente_ht = move.facture_marche_ht
            elif move.facture_amount_presente_ht and not move.facture_marche_ht:
                move.facture_marche_ht = move.facture_amount_presente_ht
            elif not move.facture_amount_presente_ht and not move.facture_marche_ht and lines_sum > 0:
                move.facture_amount_presente_ht = lines_sum
                move.facture_marche_ht = lines_sum

            presente = move.facture_amount_presente_ht or move.facture_marche_ht or lines_sum or 0.0

            if not move.facture_marche_ht and presente:
                move.facture_marche_ht = presente

            # 2. Déduction Facture N°1 perçue de 50% : TOUJOURS NÉGATIVE AVEC SIGNE MOINS (-)
            rate = move.facture_deduction_rate if (move.facture_deduction_rate is not False and move.facture_deduction_rate is not None) else 50.0
            ded_positive = (presente * rate) / 100.0
            ded_rounded = move.currency_id.round(ded_positive) if move.currency_id else round(ded_positive, 2)
            # Remplir négativement avec le signe moins
            move.facture_deduction_amount = - abs(ded_rounded)

            # 3. Montant Net de la présente facture en HTVA
            net_ht = max(0.0, presente - abs(move.facture_deduction_amount))
            move.facture_net_ht = move.currency_id.round(net_ht) if move.currency_id else round(net_ht, 2)

            # 4. Montant de la TVA 18%
            tva_rate = move.facture_tva_rate if (move.facture_tva_rate is not False and move.facture_tva_rate is not None) else 18.0
            tva = (move.facture_net_ht * tva_rate) / 100.0
            move.facture_tva_18 = move.currency_id.round(tva) if move.currency_id else round(tva, 2)

            # 5. Montant Net de la présente facture en TTC
            move.facture_net_ttc = move.facture_net_ht + move.facture_tva_18

            # 6. Arrêté en toutes lettres
            move._compute_facture_bordereau_words()

            # 7. Aperçu HTML direct
            move._compute_facture_bordereau_html()

            # 8. Mise à jour synchronisée de la ligne de facture correspondante
            if lines and len(lines) == 1 and presente > 0:
                lines[0].price_unit = presente
                if move.facture_objet:
                    lines[0].name = move.facture_objet
                if move.facture_marche_ht:
                    lines[0].montant_marche_ht = move.facture_marche_ht

    @api.depends(
        'facture_amount_presente_ht',
        'facture_marche_ht',
        'facture_deduction_rate',
        'facture_tva_rate',
        'invoice_line_ids.price_subtotal',
        'invoice_line_ids.price_unit',
        'invoice_line_ids.quantity'
    )
    def _compute_facture_bordereau_totals(self):
        for move in self:
            lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
            lines_sum = sum(l.price_subtotal if l.price_subtotal else (l.quantity * l.price_unit) for l in lines) if lines else 0.0

            if not move.facture_amount_presente_ht and lines_sum > 0:
                move.facture_amount_presente_ht = lines_sum
            elif not move.facture_amount_presente_ht and move.facture_marche_ht:
                move.facture_amount_presente_ht = move.facture_marche_ht

            if not move.facture_marche_ht and move.facture_amount_presente_ht:
                move.facture_marche_ht = move.facture_amount_presente_ht

            presente_ht = move.facture_amount_presente_ht or move.facture_marche_ht or lines_sum or 0.0

            rate = move.facture_deduction_rate if (move.facture_deduction_rate is not False and move.facture_deduction_rate is not None) else 50.0
            ded_pos = (presente_ht * rate) / 100.0
            ded = - abs(move.currency_id.round(ded_pos) if move.currency_id else round(ded_pos, 2))
            move.facture_deduction_amount = ded

            net_ht = max(0.0, presente_ht - abs(move.facture_deduction_amount or 0.0))
            move.facture_net_ht = move.currency_id.round(net_ht) if move.currency_id else round(net_ht, 2)

            tva_rate = move.facture_tva_rate if (move.facture_tva_rate is not False and move.facture_tva_rate is not None) else 18.0
            tva = (move.facture_net_ht * tva_rate) / 100.0
            move.facture_tva_18 = move.currency_id.round(tva) if move.currency_id else round(tva, 2)

            move.facture_net_ttc = move.facture_net_ht + move.facture_tva_18

    def _inverse_facture_deduction_amount(self):
        for move in self:
            presente = move.facture_amount_presente_ht or move.facture_marche_ht or 0.0
            if move.facture_deduction_amount:
                move.facture_deduction_amount = - abs(move.facture_deduction_amount)
                if presente:
                    move.facture_deduction_rate = round((abs(move.facture_deduction_amount) / presente) * 100.0, 4)

    @api.depends('facture_net_ttc', 'currency_id')
    def _compute_facture_bordereau_words(self):
        for move in self:
            try:
                # pyrefly: ignore [missing-import]
                import num2words
                words = num2words.num2words(int(round(move.facture_net_ttc or 0.0)), lang='fr')
                currency_name = move.currency_id.currency_unit_label or move.currency_id.name or 'Francs CFA'
                move.facture_net_ttc_words = f"{words.capitalize()} ({currency_name})"
            except Exception:
                move.facture_net_ttc_words = f"{move.format_monetary_value(move.facture_net_ttc)} {move.currency_id.symbol}"

    @api.depends('facture_amount_presente_ht', 'facture_deduction_label', 'facture_deduction_amount', 'facture_net_ht', 'facture_tva_18', 'facture_net_ttc', 'currency_id')
    def _compute_facture_bordereau_html(self):
        for move in self:
            curr = move.currency_id.symbol or 'FCFA'
            rows_html = ""
            for idx, line in enumerate(move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note')), 1):
                uom = line.product_uom_id.name or '-'
                line_val = line.price_subtotal if line.price_subtotal else (line.quantity * line.price_unit)
                m_marche = move.format_monetary_value(line.montant_marche_ht or line_val)
                m_presente = move.format_monetary_value(line_val)
                rows_html += f"""
                <tr style="border: 1px solid #000;">
                    <td style="border: 1px solid #000; text-align: center; padding: 4px;">{idx}</td>
                    <td style="border: 1px solid #000; padding: 4px;">{line.name or ''}</td>
                    <td style="border: 1px solid #000; text-align: center; padding: 4px;">{uom}</td>
                    <td style="border: 1px solid #000; text-align: center; padding: 4px;">{line.quantity:g}</td>
                    <td style="border: 1px solid #000; text-align: right; padding: 4px;">{m_marche}</td>
                    <td style="border: 1px solid #000; text-align: right; padding: 4px; font-weight: bold;">{m_presente}</td>
                </tr>
                """

            if not rows_html and move.facture_amount_presente_ht:
                obj = move.facture_objet or "Travaux / Prestations selon bordereau"
                m_marche = move.format_monetary_value(move.facture_marche_ht or move.facture_amount_presente_ht)
                m_presente = move.format_monetary_value(move.facture_amount_presente_ht)
                rows_html = f"""
                <tr style="border: 1px solid #000;">
                    <td style="border: 1px solid #000; text-align: center; padding: 4px;">1</td>
                    <td style="border: 1px solid #000; padding: 4px;">{obj}</td>
                    <td style="border: 1px solid #000; text-align: center; padding: 4px;">FF</td>
                    <td style="border: 1px solid #000; text-align: center; padding: 4px;">1</td>
                    <td style="border: 1px solid #000; text-align: right; padding: 4px;">{m_marche}</td>
                    <td style="border: 1px solid #000; text-align: right; padding: 4px; font-weight: bold;">{m_presente}</td>
                </tr>
                """

            move.facture_bordereau_preview_html = f"""
            <div class="table-responsive my-2">
                <table class="table table-sm table-bordered text-dark" style="border: 2px solid #000; width: 100%; border-collapse: collapse; font-size: 12.5px;">
                    <thead>
                        <tr style="background-color: #f2f2f2; border: 1px solid #000; font-weight: bold; text-align: center;">
                            <th style="border: 1px solid #000; width: 5%;">N°</th>
                            <th style="border: 1px solid #000; width: 35%;">Désignation</th>
                            <th style="border: 1px solid #000; width: 10%;">Unité</th>
                            <th style="border: 1px solid #000; width: 10%;">Quantité</th>
                            <th style="border: 1px solid #000; width: 20%;">Montant HT du marché</th>
                            <th style="border: 1px solid #000; width: 20%;">Montant de la présente facture</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html if rows_html else '<tr><td colspan="6" class="text-center text-muted p-2">Aucune ligne de facture</td></tr>'}
                        <tr style="border: 1px solid #000;">
                            <td colspan="4" style="border: 1px solid #000; padding: 4px 8px;">Montant de la présente facture en HTVA</td>
                            <td colspan="2" style="border: 1px solid #000; text-align: right; padding: 4px 8px; font-weight: bold;">{move.format_monetary_value(move.facture_amount_presente_ht)} {curr}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td colspan="4" style="border: 1px solid #000; padding: 4px 8px;">{move.facture_deduction_label or 'Montant de la facture n°1 perçue de 50%'}</td>
                            <td colspan="2" style="border: 1px solid #000; text-align: right; padding: 4px 8px; color: #dc3545;">- {move.format_monetary_value(move.facture_deduction_amount)} {curr}</td>
                        </tr>
                        <tr style="border: 1px solid #000; background-color: #eaf1f8; font-weight: bold;">
                            <td colspan="4" style="border: 1px solid #000; padding: 4px 8px; text-transform: uppercase;">MONTANT NET DE LA PRESENTE FACTURE EN HTVA</td>
                            <td colspan="2" style="border: 1px solid #000; text-align: right; padding: 4px 8px;">{move.format_monetary_value(move.facture_net_ht)} {curr}</td>
                        </tr>
                        <tr style="border: 1px solid #000;">
                            <td colspan="4" style="border: 1px solid #000; padding: 4px 8px;">Montant de la TVA 18%</td>
                            <td colspan="2" style="border: 1px solid #000; text-align: right; padding: 4px 8px;">{move.format_monetary_value(move.facture_tva_18)} {curr}</td>
                        </tr>
                        <tr style="border: 2px solid #000; background-color: #9ab7d9; font-weight: bold; font-size: 13.5px;">
                            <td colspan="4" style="border: 2px solid #000; padding: 6px 8px; text-transform: uppercase;">MONTANT NET DE LA PRESENTE FACTURE EN TTC</td>
                            <td colspan="2" style="border: 2px solid #000; text-align: right; padding: 6px 8px; font-weight: bold;">{move.format_monetary_value(move.facture_net_ttc)} {curr}</td>
                        </tr>
                    </tbody>
                </table>
                <div class="p-2 mt-2 bg-light border text-dark" style="border: 1px solid #000 !important;">
                    <strong>Arrêtée la présente facture à la somme de :</strong>
                    <span class="text-uppercase fw-bold">{move.facture_net_ttc_words or ''}</span>
                </div>
            </div>
            """

    def format_monetary_value(self, amount):
        val = abs(amount or 0.0)
        formatted = f"{val:,.2f}".replace(",", " ").replace(".", ",")
        if formatted.endswith(",00"):
            formatted = formatted[:-3]
        return formatted

    # --- DÉLÉGATION D'IMPRESSION ---
    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.facture_modele_code == 'bordereau_travaux':
            return 'btp_decompte.report_facture_bordereau_document'
        if self.decompte_id or self.facture_modele_code == 'grand_marche':
            return 'btp_decompte.report_decompte_document'
        if self.petit_marche_id or self.facture_modele_code == 'petit_marche':
            return 'btp_decompte.report_petit_marche_document'
        return super()._get_name_invoice_report()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('facture_amount_presente_ht'):
                lines_data = vals.get('invoice_line_ids') or []
                lines_total = 0.0
                for item in lines_data:
                    if isinstance(item, (list, tuple)) and len(item) == 3 and isinstance(item[2], dict):
                        d = item[2]
                        qty = d.get('quantity', 1.0)
                        price = d.get('price_unit', 0.0)
                        sub = d.get('price_subtotal', qty * price)
                        lines_total += sub
                if lines_total > 0:
                    vals['facture_amount_presente_ht'] = lines_total
                    if not vals.get('facture_marche_ht'):
                        vals['facture_marche_ht'] = lines_total

            if vals.get('facture_marche_ht') and not vals.get('facture_amount_presente_ht'):
                vals['facture_amount_presente_ht'] = vals['facture_marche_ht']
            elif vals.get('facture_amount_presente_ht') and not vals.get('facture_marche_ht'):
                vals['facture_marche_ht'] = vals['facture_amount_presente_ht']
        moves = super().create(vals_list)
        for move in moves:
            if move.facture_amount_presente_ht > 0 and not self.env.context.get('skip_sync_line'):
                lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                if not lines:
                    move.with_context(skip_sync_line=True).write({
                        'invoice_line_ids': [(0, 0, {
                            'name': move.facture_objet or _("Travaux / Prestations selon bordereau"),
                            'quantity': 1.0,
                            'price_unit': move.facture_amount_presente_ht,
                            'montant_marche_ht': move.facture_marche_ht or move.facture_amount_presente_ht,
                        })]
                    })
        return moves

    def write(self, vals):
        if 'facture_marche_ht' in vals and 'facture_amount_presente_ht' not in vals:
            for move in self:
                if not move.facture_amount_presente_ht or move.facture_amount_presente_ht == move.facture_marche_ht:
                    vals['facture_amount_presente_ht'] = vals['facture_marche_ht']
        elif 'facture_amount_presente_ht' in vals and 'facture_marche_ht' not in vals:
            for move in self:
                if not move.facture_marche_ht:
                    vals['facture_marche_ht'] = vals['facture_amount_presente_ht']
        res = super().write(vals)
        if not self.env.context.get('skip_sync_line') and ('facture_amount_presente_ht' in vals or 'facture_marche_ht' in vals or 'facture_objet' in vals):
            for move in self:
                if move.facture_amount_presente_ht > 0:
                    lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                    if not lines:
                        move.with_context(skip_sync_line=True).write({
                            'invoice_line_ids': [(0, 0, {
                                'name': move.facture_objet or _("Travaux / Prestations selon bordereau"),
                                'quantity': 1.0,
                                'price_unit': move.facture_amount_presente_ht,
                                'montant_marche_ht': move.facture_marche_ht or move.facture_amount_presente_ht,
                            })]
                        })
                    elif len(lines) == 1:
                        v = {}
                        if 'facture_amount_presente_ht' in vals and lines[0].price_unit != move.facture_amount_presente_ht:
                            v['price_unit'] = move.facture_amount_presente_ht
                        if move.facture_marche_ht and lines[0].montant_marche_ht != move.facture_marche_ht:
                            v['montant_marche_ht'] = move.facture_marche_ht
                        if move.facture_objet and lines[0].name != move.facture_objet:
                            v['name'] = move.facture_objet
                        if v:
                            lines[0].with_context(skip_sync_line=True).write(v)
        return res

    def action_print_btp_decompte(self):
        self.ensure_one()
        if not self.decompte_id:
            raise UserError(_("Cette facture n'est pas rattachée à un décompte BTP."))
        return self.env.ref('btp_decompte.action_report_btp_decompte').report_action(self.decompte_id)

    def action_print_btp_petit_marche(self):
        self.ensure_one()
        if not self.petit_marche_id:
            raise UserError(_("Cette facture n'est pas rattachée à un petit marché BTP."))
        return self.env.ref('btp_decompte.action_report_btp_petit_marche').report_action(self.petit_marche_id)

    def action_print_facture_bordereau(self):
        self.ensure_one()
        return self.env.ref('btp_decompte.action_report_facture_bordereau').report_action(self)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    line_number = fields.Integer(string='N°', compute='_compute_line_number', store=False)
    montant_marche_ht = fields.Monetary(
        string='Montant HT du marché',
        currency_field='currency_id',
        help="Montant prévisionnel ou contractuel HT du marché pour cette ligne"
    )

    def _compute_line_number(self):
        for line in self:
            if line.move_id and line.display_type not in ('line_section', 'line_note'):
                lines = line.move_id.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                line.line_number = list(lines.ids).index(line.id) + 1 if line.id in lines.ids else 1
            else:
                line.line_number = 0
