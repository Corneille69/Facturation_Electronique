# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AccountMoveDecompteBtp(models.Model):
    _inherit = 'account.move'

    # --- INFORMATIONS GÉNÉRALES DU MARCHÉ & DU DÉCOMPTE ---
    decompte_btp_marche_num = fields.Char(
        string='MARCHE N°',
        help="Référence ou numéro officiel du marché"
    )
    decompte_btp_objet = fields.Char(
        string='OBJET',
        help="Objet officiel de la prestation / travaux"
    )
    decompte_btp_financement = fields.Char(
        string='FINANCEMENT',
        help="Source de financement du marché (ex: Budget de l'État, BIDC, Banque Mondiale)"
    )
    decompte_btp_city = fields.Char(
        string='Ville de décompte',
        default='Ouagadougou',
        help="Ville affichée en haut à droite (ex: Ouagadougou)"
    )
    decompte_btp_signataire_titre = fields.Char(
        string='Titre Signataire',
        default='Le Bureau',
        help="Titre affiché au bas du document (ex: Le Bureau)"
    )
    decompte_btp_signataire_nom = fields.Char(
        string='Nom et Prénoms Signataire'
    )

    # --- TAUX DU MODÈLE (VALEURS OFFICIELLES DU DOCUMENT) ---
    decompte_btp_taux_avance = fields.Float(
        string='Taux Avance Démarrage (%)',
        default=20.0,
        help="Taux d'avance de démarrage perçue (20% selon la formule officielle du document)"
    )
    decompte_btp_taux_retenue_source = fields.Float(
        string='Taux Retenue à la Source (%)',
        default=5.0,
        help="Taux de retenue à la source (5% selon la formule officielle du document)"
    )
    decompte_btp_taux_arcop = fields.Float(
        string='Taux Retenue ARCOP (%)',
        default=0.4,
        help="Taux ARCOP opéré en une seule tranche (0,4% selon la formule officielle du document)"
    )
    decompte_btp_taux_tva = fields.Float(
        string='Taux TVA (%)',
        default=18.0,
        help="Taux de TVA officiel (18% par défaut)"
    )

    # --- VARIABLES FINANCIÈRES SAISIES PAR L'UTILISATEUR ---
    decompte_btp_a = fields.Monetary(
        string='Montant du marché HTVA (A)',
        currency_field='currency_id',
        default=0.0,
        help="MONTANT DU MARCHE EN FCFA HTVA (MHTVA) (A)"
    )
    decompte_btp_b = fields.Float(
        string='Taux d’avancement (B) (%)',
        digits=(16, 6),
        default=0.0,
        help="TAUX D’AVANCEMENT DES PRESTATIONS (TA) en (%) avec l'intégralité des chiffres après la virgule"
    )
    decompte_btp_d = fields.Monetary(
        string='Montant brut décomptes précédents (D)',
        currency_field='currency_id',
        default=0.0,
        help="MONTANT BRUT HTVA DES DECOMPTES PRECEDENTS (D)"
    )
    decompte_btp_f = fields.Monetary(
        string='Remboursement avances précédentes (F)',
        currency_field='currency_id',
        default=0.0,
        help="REMBOURSEMENT DES AVANCES PRECEDENTES (F)"
    )

    # --- LIGNES ET RÉSULTATS CALCULÉS AUTOMATIQUEMENT ---
    decompte_btp_c = fields.Monetary(
        string='Montant HTVA présent décompte (C)',
        currency_field='currency_id',
        compute='_compute_decompte_btp_values',
        store=True,
        help="(C) = (TA) x (MHTVA)"
    )
    decompte_btp_mb = fields.Monetary(
        string='Montant brut présent décompte (MB)',
        currency_field='currency_id',
        compute='_compute_decompte_btp_values',
        store=True,
        help="(MB) = (C) - (D)"
    )
    decompte_btp_e = fields.Monetary(
        string='Avance de démarrage perçue (E)',
        currency_field='currency_id',
        compute='_compute_decompte_btp_values',
        store=True,
        help="(E) = (A) x (20 / 100)"
    )
    decompte_btp_g = fields.Monetary(
        string='Remboursement avance présent décompte (G)',
        currency_field='currency_id',
        compute='_compute_decompte_btp_values',
        store=True,
        help="(G) = (E) x (B-20)/(80-20)"
    )
    decompte_btp_h = fields.Monetary(
        string='Retenue à la source (H)',
        currency_field='currency_id',
        compute='_compute_decompte_btp_values',
        store=True,
        help="(H) = (MB x 5 %)"
    )
    decompte_btp_i = fields.Monetary(
        string='Retenue ARCOP (I)',
        currency_field='currency_id',
        compute='_compute_decompte_btp_values',
        store=True,
        help="(I) = (A x 0,4 %)"
    )
    decompte_btp_tr = fields.Monetary(
        string='Total retenues (TR)',
        currency_field='currency_id',
        compute='_compute_decompte_btp_values',
        store=True,
        help="(TR) = (G + H + I)"
    )
    decompte_btp_net_htva = fields.Monetary(
        string='Montant Net Présent Décompte HTVA',
        currency_field='currency_id',
        compute='_compute_decompte_btp_values',
        store=True,
        help="MONTANT NET DU PRESENT DECOMPTE A PAYER (HTVA) = (MB) - (TR)"
    )
    decompte_btp_tva = fields.Monetary(
        string='TVA 18%',
        currency_field='currency_id',
        compute='_compute_decompte_btp_values',
        store=True,
        help="TVA 18% sur le Net HTVA"
    )
    decompte_btp_net_ttc = fields.Monetary(
        string='Montant Net Présent Décompte TTC',
        currency_field='currency_id',
        compute='_compute_decompte_btp_values',
        store=True,
        help="MONTANT NET DU PRESENT DECOMPTE A PAYER (TTC) = (Net HTVA) + (TVA)"
    )
    decompte_btp_net_lettres = fields.Char(
        string='Arrêté en toutes lettres',
        compute='_compute_decompte_btp_values',
        store=True
    )
    decompte_btp_preview_html = fields.Html(
        string='Aperçu Document',
        compute='_compute_decompte_btp_preview_html'
    )

    # --- VALIDATIONS ANTI-ERREURS ---
    @api.constrains('decompte_btp_a', 'decompte_btp_b', 'decompte_btp_d', 'decompte_btp_f')
    def _check_decompte_btp_inputs(self):
        for move in self:
            if move.facture_modele_code == 'decompte_btp':
                if move.decompte_btp_a < 0:
                    raise ValidationError(_("Le montant du marché HTVA (A) ne peut pas être négatif."))
                if move.decompte_btp_b < 0 or move.decompte_btp_b > 100:
                    raise ValidationError(_("Le taux d'avancement des prestations (B) doit être compris entre 0%% et 100%%."))
                if move.decompte_btp_d < 0:
                    raise ValidationError(_("Le montant brut des décomptes précédents (D) ne peut pas être négatif."))
                if move.decompte_btp_f < 0:
                    raise ValidationError(_("Le remboursement des avances précédentes (F) ne peut pas être négatif."))

    # --- CALCULS AUTOMATIQUES SELON LES FORMULES EXACTES DU MODÈLE ---
    @api.depends(
        'facture_modele_code',
        'decompte_btp_a',
        'decompte_btp_b',
        'decompte_btp_d',
        'decompte_btp_f',
        'decompte_btp_taux_avance',
        'decompte_btp_taux_retenue_source',
        'decompte_btp_taux_arcop',
        'decompte_btp_taux_tva',
        'currency_id'
    )
    def _compute_decompte_btp_values(self):
        for move in self:
            if move.facture_modele_code != 'decompte_btp':
                continue

            curr = move.currency_id
            def round_val(val):
                return curr.round(val) if curr else round(val, 2)

            a = move.decompte_btp_a or 0.0
            b = move.decompte_btp_b or 0.0
            d = move.decompte_btp_d or 0.0
            f = move.decompte_btp_f or 0.0

            # 1. (C) = (TA) x (MHTVA) = (B / 100) * A
            c_val = (b / 100.0) * a
            move.decompte_btp_c = round_val(c_val)

            # 2. (MB) = (C) - (D)
            mb_val = c_val - d
            move.decompte_btp_mb = round_val(mb_val)

            # 3. (E) = (A) x (20 / 100)
            taux_av = (move.decompte_btp_taux_avance or 20.0) / 100.0
            e_val = a * taux_av
            move.decompte_btp_e = round_val(e_val)

            # 4. (G) = (E) x (B - 20) / (80 - 20)
            # Règle métier : si l'avancement est <= 20%, aucun remboursement de l'avance (G = 0).
            # Si B > 20%, calcul proportionnel entre 20% et 80%. Au-delà de 80%, l'avance est entièrement remboursée (G plafonné à E).
            if b <= 20.0:
                g_val = 0.0
            elif b >= 80.0:
                g_val = e_val
            else:
                g_val = e_val * (b - 20.0) / 60.0
            move.decompte_btp_g = round_val(g_val)

            # 5. (H) Retenue à la source = (MB x 5%)
            taux_ret = (move.decompte_btp_taux_retenue_source or 5.0) / 100.0
            h_val = mb_val * taux_ret
            move.decompte_btp_h = round_val(h_val)

            # 6. (I) Retenue ARCOP = (A x 0,4%)
            taux_arcop = (move.decompte_btp_taux_arcop or 0.4) / 100.0
            i_val = a * taux_arcop
            move.decompte_btp_i = round_val(i_val)

            # 7. (TR) Total Retenues = (G + H + I)
            tr_val = g_val + h_val + i_val
            move.decompte_btp_tr = round_val(tr_val)

            # 8. MONTANT NET DU PRESENT DECOMPTE A PAYER (HTVA) = (MB) - (TR)
            net_htva_val = mb_val - tr_val
            move.decompte_btp_net_htva = round_val(net_htva_val)

            # 9. TVA 18% sur le Net HTVA
            taux_tva = (move.decompte_btp_taux_tva or 18.0) / 100.0
            tva_val = net_htva_val * taux_tva
            move.decompte_btp_tva = round_val(tva_val)

            # 10. MONTANT NET DU PRESENT DECOMPTE A PAYER (TTC) = (Net HTVA) + (TVA)
            net_ttc_val = net_htva_val + tva_val
            net_ttc_rounded = round_val(net_ttc_val)
            move.decompte_btp_net_ttc = net_ttc_rounded

            # Arrêté en toutes lettres
            try:
                # pyrefly: ignore [missing-import]
                import num2words
                words = num2words.num2words(int(round(net_ttc_rounded)), lang='fr')
                curr_name = move.currency_id.currency_unit_label or move.currency_id.name or 'Francs CFA'
                move.decompte_btp_net_lettres = f"{words.capitalize()} ({curr_name})"
            except Exception:
                val_str = f"{abs(net_ttc_rounded):,.2f}".replace(",", " ").replace(".", ",")
                if val_str.endswith(",00"):
                    val_str = val_str[:-3]
                move.decompte_btp_net_lettres = f"{val_str} {move.currency_id.symbol or 'FCFA'}"

    # --- SYNCHRONISATION ONCHANGE ---
    @api.onchange('decompte_btp_a', 'decompte_btp_b', 'decompte_btp_d', 'decompte_btp_f', 'decompte_btp_objet')
    def _onchange_decompte_btp_inputs(self):
        if self.facture_modele_code == 'decompte_btp':
            self._compute_decompte_btp_values()
            target_amt = self.decompte_btp_net_ttc or self.decompte_btp_net_htva
            if target_amt > 0:
                lines = self.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                line_name = self.decompte_btp_objet or _("Décompte de travaux BTP selon situation d'avancement")
                if lines:
                    lines[0].name = line_name
                    lines[0].price_unit = target_amt
                else:
                    self.invoice_line_ids = [(0, 0, {
                        'name': line_name,
                        'quantity': 1.0,
                        'price_unit': target_amt,
                    })]

    # --- APERÇU HTML DIRECT DU DOCUMENT ---
    @api.depends(
        'facture_modele_code',
        'decompte_btp_a',
        'decompte_btp_b',
        'decompte_btp_c',
        'decompte_btp_d',
        'decompte_btp_mb',
        'decompte_btp_e',
        'decompte_btp_f',
        'decompte_btp_g',
        'decompte_btp_h',
        'decompte_btp_i',
        'decompte_btp_tr',
        'decompte_btp_net_htva',
        'decompte_btp_tva',
        'decompte_btp_net_ttc',
        'decompte_btp_net_lettres',
        'currency_id'
    )
    def _compute_decompte_btp_preview_html(self):
        for move in self:
            if move.facture_modele_code != 'decompte_btp':
                move.decompte_btp_preview_html = False
                continue

            def fmt(val):
                return move.format_monetary_value(val)

            b_str = f"{move.decompte_btp_b:g}" if move.decompte_btp_b else "0"

            move.decompte_btp_preview_html = f"""
            <div class="table-responsive my-3">
                <table class="table table-bordered text-dark" style="border: 2px solid #000; width: 100%; border-collapse: collapse; font-size: 13px; background-color: #fff;">
                    <thead>
                        <tr style="background-color: #ffffff; border-bottom: 2px solid #000; font-weight: bold;">
                            <th style="border: 1.5px solid #000; width: 75%; padding: 7px 10px; text-transform: uppercase;">DESIGNATION</th>
                            <th style="border: 1.5px solid #000; width: 25%; padding: 7px 10px; text-align: right; text-transform: uppercase;">MONTANT</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- 1. MONTANT DU MARCHE (A) -->
                        <tr style="border: 1px solid #000; font-weight: bold;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">MONTANT DU MARCHE EN FCFA HTVA (MHTVA) (A)</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px 10px; font-weight: bold;">{fmt(move.decompte_btp_a)}</td>
                        </tr>
                        <!-- 2. TAUX D'AVANCEMENT (B) -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">TAUX D’AVANCEMENT DES PRESTATIONS (TA) en (%) <em>(l’intégralité des chiffres après la virgule)</em> (B)</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px 10px; font-weight: bold;">{b_str} %</td>
                        </tr>
                        <!-- 3. MONTANT HTVA DU PRESENT DECOMPTE (C) -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">MONTANT HTVA DU PRESENT DECOMPTE (C) = (TA) x (MHTVA)</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px 10px; font-weight: bold;">{fmt(move.decompte_btp_c)}</td>
                        </tr>
                        <!-- 4. MONTANT BRUT DES DECOMPTES PRECEDENTS (D) -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">MONTANT BRUT HTVA DES DECOMPTES PRECEDENTS (D)</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px 10px;">{fmt(move.decompte_btp_d)}</td>
                        </tr>
                        <!-- 5. MONTANT BRUT DU PRESENT DECOMPTE (MB) -->
                        <tr style="border: 1.5px solid #000; font-weight: bold; background-color: #f8f9fa;">
                            <td style="border: 1.5px solid #000; padding: 6px 10px; text-align: center; text-transform: uppercase;">MONTANT BRUT DU PRESENT DECOMPTE (MB) = (C) - (D)</td>
                            <td style="border: 1.5px solid #000; text-align: right; padding: 6px 10px; font-weight: bold;">{fmt(move.decompte_btp_mb)}</td>
                        </tr>
                        <!-- 6. AVANCE DE DEMARRAGE (E) -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">AVANCE DE DEMARRAGE PERCUE (E) = (A) x (20 / 100)</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px 10px;">{fmt(move.decompte_btp_e)}</td>
                        </tr>
                        <!-- 7. REMBOURSEMENT AVANCES PRECEDENTES (F) -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">REMBOURSEMENT DES AVANCES PRECEDENTES (F)</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px 10px;">{fmt(move.decompte_btp_f)}</td>
                        </tr>
                        <!-- 8. LIGNE SEPARATRICE : RETENUES A OPERER -->
                        <tr style="border: 1.5px solid #000; background-color: #f1f3f5; font-weight: bold;">
                            <td colspan="2" style="border: 1.5px solid #000; text-align: center; padding: 6px 10px; text-transform: uppercase; letter-spacing: 0.5px;">RETENUES A OPERER</td>
                        </tr>
                        <!-- 9. REMBOURSEMENT AVANCE PRESENT DECOMPTE (G) -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">REMBOURSEMENT DE L’AVANCE DU PRESENT DECOMPTE (G) = (E) x (B-20)/(80-20)</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px 10px; color: #dc3545;">- {fmt(move.decompte_btp_g)}</td>
                        </tr>
                        <!-- 10. RETENUE A LA SOURCE (H) -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">RETENUE A LA SOURCE = (MB x 5%) (H)</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px 10px; color: #dc3545;">- {fmt(move.decompte_btp_h)}</td>
                        </tr>
                        <!-- 11. RETENUE ARCOP (I) -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; padding: 6px 10px;">RETENUE ARCOP <em>(retenue opérée en une seule tranche)</em> (A x 0,4%) (I)</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px 10px; color: #dc3545;">- {fmt(move.decompte_btp_i)}</td>
                        </tr>
                        <!-- 12. TOTAL RETENUES (TR) -->
                        <tr style="border: 1.5px solid #000; font-weight: bold; background-color: #fdfdfe;">
                            <td style="border: 1.5px solid #000; text-align: center; padding: 6px 10px; text-transform: uppercase;">TOTAL RETENUES (TR) = (G+H+I)</td>
                            <td style="border: 1.5px solid #000; text-align: right; padding: 6px 10px; font-weight: bold; color: #dc3545;">- {fmt(move.decompte_btp_tr)}</td>
                        </tr>
                        <!-- 13. MONTANT NET DECOMPTE (HTVA) -->
                        <tr style="border: 1.5px solid #000; font-weight: bold; background-color: #eaf2f8;">
                            <td style="border: 1.5px solid #000; padding: 7px 10px; text-align: center; text-transform: uppercase;">MONTANT NET DU PRESENT DECOMPTE A PAYER (HTVA) = (MB) - (TR)</td>
                            <td style="border: 1.5px solid #000; text-align: right; padding: 7px 10px; font-weight: bold; color: #1a5276;">{fmt(move.decompte_btp_net_htva)}</td>
                        </tr>
                        <!-- 14. TVA 18% -->
                        <tr style="border: 1px solid #000; font-weight: 500;">
                            <td style="border: 1px solid #000; text-align: center; padding: 6px 10px;">TVA 18%</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px 10px;">{fmt(move.decompte_btp_tva)}</td>
                        </tr>
                        <!-- 15. MONTANT NET DECOMPTE (TTC) -->
                        <tr style="border: 2px solid #000; font-weight: bold; font-size: 14px; background-color: #d4efdf;">
                            <td style="border: 2px solid #000; padding: 8px 10px; text-align: center; text-transform: uppercase; color: #145a32;">MONTANT NET DU PRESENT DECOMPTE A PAYER (TTC)</td>
                            <td style="border: 2px solid #000; text-align: right; padding: 8px 10px; font-weight: bold; color: #145a32;">{fmt(move.decompte_btp_net_ttc)}</td>
                        </tr>
                    </tbody>
                </table>
                <div class="p-2 mt-2 bg-light border text-dark" style="border: 1.5px solid #000 !important; font-size: 13px;">
                    <strong>Arrêté la présente facture à la somme de :</strong>
                    <span class="text-uppercase fw-bold ms-1">{move.decompte_btp_net_lettres or ''}</span>
                </div>
            </div>
            """

    # --- DÉLÉGATION DU RAPPORT D'IMPRESSION PDF ---
    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.facture_modele_code == 'decompte_btp':
            return 'btp_decompte.report_facture_decompte_document'
        return super()._get_name_invoice_report()

    def action_print_facture_decompte(self):
        self.ensure_one()
        return self.env.ref('btp_decompte.action_report_facture_decompte').report_action(self)

    # --- SYNCHRONISATION COMPTABLE STANDARD ODOO (ACTION_POST) ---
    def action_post(self):
        for move in self:
            if move.facture_modele_code == 'decompte_btp':
                move._compute_decompte_btp_values()
                target_amt = move.decompte_btp_net_ttc or move.decompte_btp_net_htva
                lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                line_name = move.decompte_btp_objet or _("Situation de décompte de travaux BTP")
                if not lines and target_amt > 0:
                    move.with_context(skip_sync_decompte=True).write({
                        'invoice_line_ids': [(0, 0, {
                            'name': line_name,
                            'quantity': 1.0,
                            'price_unit': target_amt,
                        })]
                    })
                elif lines and target_amt > 0 and len(lines) == 1:
                    lines[0].with_context(skip_sync_decompte=True).write({
                        'price_unit': target_amt,
                        'name': line_name,
                    })
        return super().action_post()

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.facture_modele_code == 'decompte_btp' and not self.env.context.get('skip_sync_decompte'):
                move._compute_decompte_btp_values()
                target_amt = move.decompte_btp_net_ttc or move.decompte_btp_net_htva
                lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                if not lines and target_amt > 0:
                    move.with_context(skip_sync_decompte=True).write({
                        'invoice_line_ids': [(0, 0, {
                            'name': move.decompte_btp_objet or _("Situation de décompte de travaux BTP"),
                            'quantity': 1.0,
                            'price_unit': target_amt,
                        })]
                    })
        return moves

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('skip_sync_decompte') and any(k in vals for k in ('decompte_btp_a', 'decompte_btp_b', 'decompte_btp_d', 'decompte_btp_f', 'decompte_btp_objet')):
            for move in self:
                if move.facture_modele_code == 'decompte_btp':
                    move._compute_decompte_btp_values()
                    target_amt = move.decompte_btp_net_ttc or move.decompte_btp_net_htva
                    lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                    if lines and len(lines) == 1 and target_amt > 0:
                        lines[0].with_context(skip_sync_decompte=True).write({
                            'price_unit': target_amt,
                            'name': move.decompte_btp_objet or lines[0].name,
                        })
                    elif not lines and target_amt > 0:
                        move.with_context(skip_sync_decompte=True).write({
                            'invoice_line_ids': [(0, 0, {
                                'name': move.decompte_btp_objet or _("Situation de décompte de travaux BTP"),
                                'quantity': 1.0,
                                'price_unit': target_amt,
                            })]
                        })
        return res
