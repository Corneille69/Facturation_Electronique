# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class BtpFactureEtudeLine(models.Model):
    _name = 'btp.facture.etude.line'
    _description = 'Ligne de Prestation Études & Honoraires BTP'
    _order = 'sequence asc, id asc'

    move_id = fields.Many2one(
        'account.move',
        string='Facture',
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(string='Séquence', default=10)
    section = fields.Selection([
        ('section_1', 'I — HONORAIRES'),
        ('section_2', 'II — FRAIS REMBOURSABLE'),
        ('section_3', 'III — FRAIS DIVERS'),
    ], string='Section', required=True, default='section_1')

    line_number = fields.Char(string='N°', help="Numérotation officielle (ex: I.1, II.1, III.1)")
    name = fields.Char(string='Désignation', required=True)
    unite = fields.Char(string='Unité', default='Mois')
    quantity = fields.Float(string='Quantité', default=1.0)
    price_unit = fields.Monetary(
        string='Prix Unitaire',
        currency_field='currency_id',
        default=0.0
    )
    price_total = fields.Monetary(
        string='Prix Total',
        currency_field='currency_id',
        compute='_compute_price_total',
        store=True
    )
    currency_id = fields.Many2one(related='move_id.currency_id', readonly=True)

    @api.depends('quantity', 'price_unit', 'currency_id')
    def _compute_price_total(self):
        for line in self:
            qty = line.quantity or 0.0
            pu = line.price_unit or 0.0
            total = qty * pu
            line.price_total = line.currency_id.round(total) if line.currency_id else round(total, 2)

    @api.constrains('quantity', 'price_unit')
    def _check_quantities(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_("La quantité de la ligne %s ne peut pas être négative.") % (line.name or ''))
            if line.price_unit < 0:
                raise ValidationError(_("Le prix unitaire de la ligne %s ne peut pas être négatif.") % (line.name or ''))


class AccountMoveEtudes(models.Model):
    _inherit = 'account.move'

    # --- LIGNES DE PRESTATIONS DES 3 SECTIONS ---
    etude_line_ids = fields.One2many(
        'btp.facture.etude.line',
        'move_id',
        string='Lignes de Prestations Études',
        copy=True
    )

    # --- INFORMATIONS GÉNÉRALES DU MARCHÉ & DE LA FACTURE ---
    etude_marche_num = fields.Char(
        string='Marché N°',
        help="Référence ou numéro officiel du marché"
    )
    etude_marche_montant = fields.Monetary(
        string='Montant du Marché',
        currency_field='currency_id',
        default=0.0,
        help="Montant contractuel global du marché"
    )
    etude_financement = fields.Char(
        string='Financement',
        help="Bailleur de fonds ou source de financement (ex: Budget de l'État, BIDC, Banque Mondiale)"
    )
    etude_objet = fields.Char(
        string='OBJET',
        help="Objet officiel de la prestation / étude"
    )
    etude_city = fields.Char(
        string='Ville de facturation',
        default='Ouagadougou',
        help="Ville affichée en haut à droite (ex: Ouagadougou)"
    )
    etude_signataire_titre = fields.Char(
        string='Titre Signataire',
        default='Le Bureau',
        help="Titre affiché sous l'arrêté de la facture (ex: Le Bureau)"
    )
    etude_signataire_nom = fields.Char(
        string='Nom et Prénoms Signataire'
    )
    etude_tva_rate = fields.Float(
        string='Taux TVA (%)',
        default=18.0,
        help="Taux officiel de la TVA (18% par défaut)"
    )

    # --- SOUS-TOTAUX DES SECTIONS & TOTAUX GÉNÉRAUX ---
    etude_sous_total_1 = fields.Monetary(
        string='SOUS TOTAL I (Honoraires)',
        currency_field='currency_id',
        compute='_compute_etude_totals',
        store=True
    )
    etude_sous_total_2 = fields.Monetary(
        string='SOUS TOTAL II (Frais Remboursable)',
        currency_field='currency_id',
        compute='_compute_etude_totals',
        store=True
    )
    etude_sous_total_3 = fields.Monetary(
        string='SOUS TOTAL III (Frais Divers)',
        currency_field='currency_id',
        compute='_compute_etude_totals',
        store=True
    )
    etude_total_htva = fields.Monetary(
        string='TOTAL GENERAL HTVA',
        currency_field='currency_id',
        compute='_compute_etude_totals',
        store=True
    )
    etude_total_tva = fields.Monetary(
        string='TVA 18%',
        currency_field='currency_id',
        compute='_compute_etude_totals',
        store=True
    )
    etude_net_a_payer = fields.Monetary(
        string='MONTANT NET A PAYER',
        currency_field='currency_id',
        compute='_compute_etude_totals',
        store=True
    )
    etude_net_lettres = fields.Char(
        string='Arrêtée en toutes lettres',
        compute='_compute_etude_totals',
        store=True
    )
    etude_preview_html = fields.Html(
        string='Aperçu Document',
        compute='_compute_etude_preview_html'
    )

    # --- INITIALISATION AUTOMATIQUE DES 10 LIGNES TYPES DE LA PHOTO ---
    def action_init_default_etude_lines(self):
        self.ensure_one()
        if self.facture_modele_code != 'honoraires_etudes':
            return

        default_lines = [
            # SECTION I : HONORAIRES
            {'section': 'section_1', 'line_number': 'I.1', 'name': 'Chef de mission', 'unite': 'Mois', 'quantity': 1.0, 'sequence': 10},
            {'section': 'section_1', 'line_number': 'I.2', 'name': 'Ingénieur routier', 'unite': 'Mois', 'quantity': 1.0, 'sequence': 20},
            {'section': 'section_1', 'line_number': 'I.3', 'name': 'Ingénieur hydrologue / hydraulicien', 'unite': 'Mois', 'quantity': 1.0, 'sequence': 30},
            # SECTION II : FRAIS REMBOURSABLE
            {'section': 'section_2', 'line_number': 'II.1', 'name': 'Frais Homologues', 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 40},
            {'section': 'section_2', 'line_number': 'II.2', 'name': 'Ateliers de restitution et de validation des études', 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 50},
            # SECTION III : FRAIS DIVERS
            {'section': 'section_3', 'line_number': 'III.1', 'name': 'Fonctionnement de la mission', 'unite': 'Mois', 'quantity': 1.0, 'sequence': 60},
            {'section': 'section_3', 'line_number': 'III.2', 'name': 'Enquête de trafic et investigation de terrain', 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 70},
            {'section': 'section_3', 'line_number': 'III.3', 'name': 'Equipe géotechnique et de laboratoire', 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 80},
            {'section': 'section_3', 'line_number': 'III.4', 'name': 'Equipement topographique', 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 90},
            {'section': 'section_3', 'line_number': 'III.5', 'name': "Sortie de l'équipe de l'Agence National des Evaluations Environnementales", 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 100},
        ]

        # Supprimer les lignes existantes si demandées et réinitialiser
        self.etude_line_ids.unlink()
        lines_vals = [(0, 0, vals) for vals in default_lines]
        self.write({'etude_line_ids': lines_vals})
        self._compute_etude_totals()

    # --- CALCULS AUTOMATIQUES DES SOUS-TOTAUX, HTVA, TVA 18% ET NET À PAYER ---
    @api.depends(
        'facture_modele_code',
        'etude_line_ids.price_total',
        'etude_line_ids.section',
        'etude_tva_rate',
        'currency_id'
    )
    def _compute_etude_totals(self):
        for move in self:
            if move.facture_modele_code != 'honoraires_etudes':
                continue

            curr = move.currency_id
            def round_val(val):
                return curr.round(val) if curr else round(val, 2)

            lines_1 = move.etude_line_ids.filtered(lambda l: l.section == 'section_1')
            lines_2 = move.etude_line_ids.filtered(lambda l: l.section == 'section_2')
            lines_3 = move.etude_line_ids.filtered(lambda l: l.section == 'section_3')

            s1 = round_val(sum(lines_1.mapped('price_total')))
            s2 = round_val(sum(lines_2.mapped('price_total')))
            s3 = round_val(sum(lines_3.mapped('price_total')))

            move.etude_sous_total_1 = s1
            move.etude_sous_total_2 = s2
            move.etude_sous_total_3 = s3

            # TOTAL GENERAL HTVA = Sous-total I + II + III
            total_htva = round_val(s1 + s2 + s3)
            move.etude_total_htva = total_htva

            # TVA 18% = Total Général HTVA * 18%
            tva_rate = (move.etude_tva_rate or 18.0) / 100.0
            tva = round_val(total_htva * tva_rate)
            move.etude_total_tva = tva

            # MONTANT NET A PAYER = Total Général HTVA + TVA 18%
            net = round_val(total_htva + tva)
            move.etude_net_a_payer = net

            # Conversion en toutes lettres
            try:
                # pyrefly: ignore [missing-import]
                import num2words
                words = num2words.num2words(int(round(net)), lang='fr')
                curr_name = move.currency_id.currency_unit_label or move.currency_id.name or 'Francs CFA'
                move.etude_net_lettres = f"{words.capitalize()} ({curr_name})"
            except Exception:
                move.etude_net_lettres = f"{move.format_monetary_value(net)} {move.currency_id.symbol or 'FCFA'}"

    # --- SYNCHRONISATION ONCHANGE ---
    @api.onchange('facture_modele_id')
    def _onchange_facture_modele_etudes(self):
        if self.facture_modele_code == 'honoraires_etudes':
            if not self.etude_line_ids:
                default_lines = [
                    (0, 0, {'section': 'section_1', 'line_number': 'I.1', 'name': 'Chef de mission', 'unite': 'Mois', 'quantity': 1.0, 'sequence': 10}),
                    (0, 0, {'section': 'section_1', 'line_number': 'I.2', 'name': 'Ingénieur routier', 'unite': 'Mois', 'quantity': 1.0, 'sequence': 20}),
                    (0, 0, {'section': 'section_1', 'line_number': 'I.3', 'name': 'Ingénieur hydrologue / hydraulicien', 'unite': 'Mois', 'quantity': 1.0, 'sequence': 30}),
                    (0, 0, {'section': 'section_2', 'line_number': 'II.1', 'name': 'Frais Homologues', 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 40}),
                    (0, 0, {'section': 'section_2', 'line_number': 'II.2', 'name': 'Ateliers de restitution et de validation des études', 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 50}),
                    (0, 0, {'section': 'section_3', 'line_number': 'III.1', 'name': 'Fonctionnement de la mission', 'unite': 'Mois', 'quantity': 1.0, 'sequence': 60}),
                    (0, 0, {'section': 'section_3', 'line_number': 'III.2', 'name': 'Enquête de trafic et investigation de terrain', 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 70}),
                    (0, 0, {'section': 'section_3', 'line_number': 'III.3', 'name': 'Equipe géotechnique et de laboratoire', 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 80}),
                    (0, 0, {'section': 'section_3', 'line_number': 'III.4', 'name': 'Equipement topographique', 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 90}),
                    (0, 0, {'section': 'section_3', 'line_number': 'III.5', 'name': "Sortie de l'équipe de l'Agence National des Evaluations Environnementales", 'unite': 'Forfait', 'quantity': 1.0, 'sequence': 100}),
                ]
                self.etude_line_ids = default_lines

    # --- APERÇU HTML DIRECT DANS LE FORMULAIRE ---
    @api.depends(
        'facture_modele_code',
        'etude_line_ids.line_number',
        'etude_line_ids.name',
        'etude_line_ids.unite',
        'etude_line_ids.quantity',
        'etude_line_ids.price_unit',
        'etude_line_ids.price_total',
        'etude_sous_total_1',
        'etude_sous_total_2',
        'etude_sous_total_3',
        'etude_total_htva',
        'etude_total_tva',
        'etude_net_a_payer',
        'etude_net_lettres',
        'currency_id'
    )
    def _compute_etude_preview_html(self):
        for move in self:
            if move.facture_modele_code != 'honoraires_etudes':
                move.etude_preview_html = False
                continue

            def fmt(val):
                return move.format_monetary_value(val)

            def render_section(section_code, title, st_name, st_val):
                lines = move.etude_line_ids.filtered(lambda l: l.section == section_code)
                html = f"""
                <tr style="background-color: #f8f9fa; border: 1.5px solid #000; font-weight: bold;">
                    <td style="border: 1.5px solid #000; text-align: center; padding: 4px 6px;">{'I' if section_code == 'section_1' else ('II' if section_code == 'section_2' else 'III')}</td>
                    <td colspan="5" style="border: 1.5px solid #000; padding: 4px 8px; text-transform: uppercase;">{title}</td>
                </tr>
                """
                for l in lines:
                    html += f"""
                    <tr style="border: 1px solid #000;">
                        <td style="border: 1px solid #000; text-align: center; padding: 4px;">{l.line_number or ''}</td>
                        <td style="border: 1px solid #000; padding: 4px 8px;">{l.name or ''}</td>
                        <td style="border: 1px solid #000; text-align: center; padding: 4px;">{l.unite or ''}</td>
                        <td style="border: 1px solid #000; text-align: center; padding: 4px;">{l.quantity:g}</td>
                        <td style="border: 1px solid #000; text-align: right; padding: 4px 8px;">{fmt(l.price_unit)}</td>
                        <td style="border: 1px solid #000; text-align: right; padding: 4px 8px; font-weight: bold;">{fmt(l.price_total)}</td>
                    </tr>
                    """
                html += f"""
                <tr style="border: 1.5px solid #000; font-weight: bold; background-color: #fdfdfe;">
                    <td colspan="5" style="border: 1.5px solid #000; text-align: right; padding: 5px 12px; font-weight: bold; letter-spacing: 0.5px;">{st_name}</td>
                    <td style="border: 1.5px solid #000; text-align: right; padding: 5px 8px; font-weight: bold;">{fmt(st_val)}</td>
                </tr>
                """
                return html

            s1_html = render_section('section_1', 'HONORAIRES', 'SOUS TOTAL I', move.etude_sous_total_1)
            s2_html = render_section('section_2', 'FRAIS REMBOURSABLE', 'SOUS TOTAL II', move.etude_sous_total_2)
            s3_html = render_section('section_3', 'FRAIS DIVERS', 'SOUS TOTAL III', move.etude_sous_total_3)

            move.etude_preview_html = f"""
            <div class="table-responsive my-3">
                <table class="table table-bordered text-dark" style="border: 2px solid #000; width: 100%; border-collapse: collapse; font-size: 12.5px; background-color: #fff;">
                    <thead>
                        <tr style="background-color: #ffffff; border-bottom: 2px solid #000; font-weight: bold; text-align: center;">
                            <th style="border: 1.5px solid #000; width: 6%; padding: 6px 3px;">N°</th>
                            <th style="border: 1.5px solid #000; width: 44%; padding: 6px 8px; text-align: left;">DESIGNATIONS</th>
                            <th style="border: 1.5px solid #000; width: 10%; padding: 6px 3px;">UNITE</th>
                            <th style="border: 1.5px solid #000; width: 10%; padding: 6px 3px;">QUANTITE</th>
                            <th style="border: 1.5px solid #000; width: 15%; padding: 6px 4px;">PRIX UNITAIRE</th>
                            <th style="border: 1.5px solid #000; width: 15%; padding: 6px 4px;">PRIX TOTAL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {s1_html}
                        {s2_html}
                        {s3_html}
                        <!-- TOTAL GENERAL HTVA -->
                        <tr style="border: 1.5px solid #000; font-weight: bold; background-color: #f1f3f5;">
                            <td colspan="5" style="border: 1.5px solid #000; padding: 6px 8px; text-transform: uppercase;">TOTAL GENERAL HTVA</td>
                            <td style="border: 1.5px solid #000; text-align: right; padding: 6px 8px; font-weight: bold;">{fmt(move.etude_total_htva)}</td>
                        </tr>
                        <!-- TVA 18% -->
                        <tr style="border: 1px solid #000; font-weight: 500;">
                            <td colspan="5" style="border: 1px solid #000; padding: 5px 8px;">TVA 18%</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 5px 8px;">{fmt(move.etude_total_tva)}</td>
                        </tr>
                        <!-- MONTANT NET A PAYER -->
                        <tr style="border: 2px solid #000; font-weight: bold; font-size: 13.5px; background-color: #e9ecef;">
                            <td colspan="5" style="border: 2px solid #000; padding: 7px 8px; text-transform: uppercase;">MONTANT NET A PAYER</td>
                            <td style="border: 2px solid #000; text-align: right; padding: 7px 8px; font-weight: bold;">{fmt(move.etude_net_a_payer)}</td>
                        </tr>
                    </tbody>
                </table>
                <div class="p-2 mt-2 bg-light border text-dark" style="border: 1.5px solid #000 !important; font-size: 12.5px;">
                    <strong>Arretez la présente facture a la somme de :</strong>
                    <span class="text-uppercase fw-bold ms-1">{move.etude_net_lettres or ''}</span>
                </div>
            </div>
            """

    # --- DÉLÉGATION D'IMPRESSION DU RAPPORT PDF ---
    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.facture_modele_code == 'honoraires_etudes':
            return 'btp_decompte.report_facture_etudes_document'
        return super()._get_name_invoice_report()

    def action_print_facture_etudes(self):
        self.ensure_one()
        return self.env.ref('btp_decompte.action_report_facture_etudes').report_action(self)

    # --- CREATE & WRITE : SYNCHRONISATION COMPTABLE STANDARD ODOO ---
    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.facture_modele_code == 'honoraires_etudes' and not self.env.context.get('skip_sync_etude'):
                move._compute_etude_totals()
                target_amt = move.etude_net_a_payer or move.etude_total_htva
                lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                if not lines and target_amt > 0:
                    move.with_context(skip_sync_etude=True).write({
                        'invoice_line_ids': [(0, 0, {
                            'name': move.etude_objet or _("Études et Prestations d'ingénierie selon bordereau"),
                            'quantity': 1.0,
                            'price_unit': target_amt,
                        })]
                    })
        return moves

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('skip_sync_etude') and any(k in vals for k in ('etude_line_ids', 'etude_objet', 'etude_tva_rate')):
            for move in self:
                if move.facture_modele_code == 'honoraires_etudes':
                    move._compute_etude_totals()
                    target_amt = move.etude_net_a_payer or move.etude_total_htva
                    lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                    if lines and len(lines) == 1 and target_amt > 0:
                        lines[0].with_context(skip_sync_etude=True).write({
                            'price_unit': target_amt,
                            'name': move.etude_objet or lines[0].name,
                        })
                    elif not lines and target_amt > 0:
                        move.with_context(skip_sync_etude=True).write({
                            'invoice_line_ids': [(0, 0, {
                                'name': move.etude_objet or _("Études et Prestations d'ingénierie selon bordereau"),
                                'quantity': 1.0,
                                'price_unit': target_amt,
                            })]
                        })
        return res

    def action_post(self):
        for move in self:
            if move.facture_modele_code == 'honoraires_etudes':
                move._compute_etude_totals()
                target_amt = move.etude_net_a_payer or move.etude_total_htva
                lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                if not lines and target_amt > 0:
                    move.with_context(skip_sync_etude=True).write({
                        'invoice_line_ids': [(0, 0, {
                            'name': move.etude_objet or _("Études et Prestations d'ingénierie selon bordereau"),
                            'quantity': 1.0,
                            'price_unit': target_amt,
                        })]
                    })
                elif lines and target_amt > 0 and len(lines) == 1:
                    lines[0].with_context(skip_sync_etude=True).write({
                        'price_unit': target_amt,
                        'name': move.etude_objet or lines[0].name,
                    })
        return super().action_post()
