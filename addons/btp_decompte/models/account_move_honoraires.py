# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AccountMoveHonoraires(models.Model):
    _inherit = 'account.move'

    # --- INFORMATIONS GÉNÉRALES DU MODÈLE HONORAIRES ---
    honoraire_montant = fields.Monetary(
        string='Honoraires des consultants (Ligne 1)',
        currency_field='currency_id',
        default=0.0,
        help="Montant total des honoraires des consultants convenu dans le contrat"
    )
    honoraire_frais_remboursables = fields.Monetary(
        string='Frais Remboursables (Ligne 2)',
        currency_field='currency_id',
        default=0.0,
        help="Montant des frais remboursables (déplacements, hébergements, rapports et communications 100%)"
    )
    honoraire_unite = fields.Char(
        string='Unité',
        default='Forfait',
        help="Unité de mesure de la prestation (ex: Forfait, Mois, Mission)"
    )
    honoraire_quantite = fields.Float(
        string='Quantité',
        default=1.0,
        help="Quantité de la prestation"
    )
    honoraire_objet = fields.Char(
        string='Objet de la mission',
        help="Libellé de la mission ou prestation tel qu'affiché sur la facture"
    )
    honoraire_city = fields.Char(
        string='Ville de facturation',
        default='Ouagadougou',
        help="Nom de la ville affichée en haut à droite (ex: Ouagadougou)"
    )
    honoraire_signataire_titre = fields.Char(
        string='Titre du Signataire',
        default='Signataire',
        help="Titre affiché sous la signature (ex: Signataire, Le Consultant)"
    )
    honoraire_signataire_nom = fields.Char(
        string='Nom et Prénoms',
        help="Nom et prénoms du signataire affiché au bas du document"
    )

    # --- TAUX DU MODÈLE (CONFIGURABLES) ---
    honoraire_taux_tranche_1 = fields.Float(
        string='Taux Tranche 1 Honoraires (%)',
        default=30.0,
        help="Pourcentage d'avance de la 1ère tranche sur les honoraires (30% par défaut)"
    )
    honoraire_taux_tranche_2 = fields.Float(
        string='Taux Tranche 2 Honoraires (%)',
        default=30.0,
        help="Pourcentage de la 2ème tranche sur les honoraires après 50% d'exécution (30% par défaut)"
    )
    honoraire_taux_tranche_3 = fields.Float(
        string='Taux Tranche 3 Honoraires (%)',
        default=40.0,
        help="Pourcentage de la 3ème tranche sur les honoraires après 100% d'exécution (40% par défaut)"
    )
    honoraire_taux_retenue = fields.Float(
        string='Taux Retenue à la source (%)',
        default=5.0,
        help="Pourcentage de retenue à la source sur le montant total de la prestation (5% par défaut)"
    )

    # --- SUIVI DE L'AVANCEMENT DE LA PRESTATION ---
    honoraire_prestation_50 = fields.Boolean(
        string='Prestation exécutée à 50%',
        default=False,
        help="Cocher lorsque la prestation a atteint au moins 50% d'exécution pour débloquer la tranche 2"
    )
    honoraire_prestation_100 = fields.Boolean(
        string='Prestation exécutée à 100%',
        default=False,
        help="Cocher lorsque la prestation est achevée à 100% pour débloquer la tranche 3"
    )

    # --- LES 10 LIGNES OFFICIELLES DU MODÈLE ---
    honoraire_line_1_montant = fields.Monetary(
        string='Ligne 1 : Honoraires des consultants',
        currency_field='currency_id',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_line_2_montant = fields.Monetary(
        string='Ligne 2 : Frais Remboursable (100%)',
        currency_field='currency_id',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_line_3_total_prestation = fields.Monetary(
        string='Ligne 3 : Montant total de la prestation',
        currency_field='currency_id',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_line_4_tranche_1_honoraire = fields.Monetary(
        string='Ligne 4 : Paiement 1ere tranche (Avance 30% Honoraire)',
        currency_field='currency_id',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_line_5_tranche_1_frais = fields.Monetary(
        string='Ligne 5 : Paiement 1ere tranche (100% Frais remboursable)',
        currency_field='currency_id',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_line_6_total_tranche_1 = fields.Monetary(
        string='Ligne 6 : Total règlement 1ere Tranche',
        currency_field='currency_id',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_line_7_tranche_2_honoraire = fields.Monetary(
        string='Ligne 7 : Paiement 2 ème Tranche 30%Honoraire',
        currency_field='currency_id',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_line_8_tranche_3_honoraire = fields.Monetary(
        string='Ligne 8 : Paiement 3 ème Tranche 40%Honoraire',
        currency_field='currency_id',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_line_9_retenue_source = fields.Monetary(
        string='Ligne 9 : Retenue à la source (5% Tranche 1+2+3)',
        currency_field='currency_id',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_line_10_net_a_payer = fields.Monetary(
        string='Ligne 10 : Net à payer Tranche 2+3',
        currency_field='currency_id',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_net_lettres = fields.Char(
        string='Arrêtée en toutes lettres',
        compute='_compute_honoraire_lines',
        store=True
    )
    honoraire_preview_html = fields.Html(
        string='Aperçu du Tableau',
        compute='_compute_honoraire_preview_html'
    )

    # --- VALIDATIONS ANTI-ERREURS ---
    @api.constrains('honoraire_montant', 'honoraire_frais_remboursables', 'honoraire_quantite')
    def _check_honoraire_values(self):
        for move in self:
            if move.facture_modele_code == 'honoraires_consultant':
                if move.honoraire_montant < 0:
                    raise ValidationError(_("Le montant des honoraires ne peut pas être négatif."))
                if move.honoraire_frais_remboursables < 0:
                    raise ValidationError(_("Le montant des frais remboursables ne peut pas être négatif."))
                if move.honoraire_quantite < 0:
                    raise ValidationError(_("La quantité ne peut pas être négative."))
                if move.honoraire_taux_tranche_1 < 0 or move.honoraire_taux_tranche_2 < 0 or move.honoraire_taux_tranche_3 < 0:
                    raise ValidationError(_("Les pourcentages des tranches ne peuvent pas être négatifs."))
                if move.honoraire_taux_retenue < 0:
                    raise ValidationError(_("Le taux de retenue à la source ne peut pas être négatif."))

    # --- CALCULS AUTOMATIQUES DES 10 LIGNES MÉTIER ---
    @api.depends(
        'facture_modele_code',
        'honoraire_montant',
        'honoraire_frais_remboursables',
        'honoraire_taux_tranche_1',
        'honoraire_taux_tranche_2',
        'honoraire_taux_tranche_3',
        'honoraire_taux_retenue',
        'currency_id'
    )
    def _compute_honoraire_lines(self):
        for move in self:
            if move.facture_modele_code != 'honoraires_consultant':
                continue

            curr = move.currency_id
            def round_val(val):
                return curr.round(val) if curr else round(val, 2)

            # 1. Honoraires des consultants
            h = round_val(move.honoraire_montant or 0.0)
            move.honoraire_line_1_montant = h

            # 2. Frais Remboursables (100%)
            f = round_val(move.honoraire_frais_remboursables or 0.0)
            move.honoraire_line_2_montant = f

            # 3. Montant total de la prestation = Ligne 1 + Ligne 2
            total_prestation = round_val(h + f)
            move.honoraire_line_3_total_prestation = total_prestation

            # 4. Paiement 1ere tranche (Avance 30% Honoraire)
            t1_rate = (move.honoraire_taux_tranche_1 or 30.0) / 100.0
            l4 = round_val(h * t1_rate)
            move.honoraire_line_4_tranche_1_honoraire = l4

            # 5. Paiement 1ere tranche (100% Frais remboursable)
            l5 = f
            move.honoraire_line_5_tranche_1_frais = l5

            # 6. Total règlement 1ere Tranche = Ligne 4 + Ligne 5
            l6 = round_val(l4 + l5)
            move.honoraire_line_6_total_tranche_1 = l6

            # 7. Paiement 2 ème Tranche 30%Honoraire (Après 50% de prestation exécutée)
            t2_rate = (move.honoraire_taux_tranche_2 or 30.0) / 100.0
            l7 = round_val(h * t2_rate)
            move.honoraire_line_7_tranche_2_honoraire = l7

            # 8. Paiement 3 ème Tranche 40%Honoraire (Après 100% de prestation exécutée)
            t3_rate = (move.honoraire_taux_tranche_3 or 40.0) / 100.0
            l8 = round_val(h * t3_rate)
            move.honoraire_line_8_tranche_3_honoraire = l8

            # 9. Retenue à la source (5% Tranche 1+2+3) = 5% sur le total de la prestation
            # Démonstration : Tranche 1 (30% H + F) + Tranche 2 (30% H) + Tranche 3 (40% H) = (30%+30%+40%)H + F = H + F = Total Prestation
            ret_rate = (move.honoraire_taux_retenue or 5.0) / 100.0
            l9 = round_val(total_prestation * ret_rate)
            move.honoraire_line_9_retenue_source = l9

            # 10. Net à payer Tranche 2+3 = (Ligne 7 + Ligne 8) - Ligne 9
            # Formule officielle conforme aux libellés du document : (Tranche 2 + Tranche 3) - Retenue 5%
            l10 = round_val((l7 + l8) - l9)
            move.honoraire_line_10_net_a_payer = l10

            # Arrêté en toutes lettres
            try:
                # pyrefly: ignore [missing-import]
                import num2words
                words = num2words.num2words(int(round(l10)), lang='fr')
                curr_name = move.currency_id.currency_unit_label or move.currency_id.name or 'Francs CFA'
                move.honoraire_net_lettres = f"{words.capitalize()} ({curr_name})"
            except Exception:
                move.honoraire_net_lettres = f"{move.format_monetary_value(l10)} {move.currency_id.symbol or 'FCFA'}"

    # --- SYNCHRONISATION ONCHANGE ---
    @api.onchange('honoraire_montant', 'honoraire_frais_remboursables', 'honoraire_objet', 'honoraire_quantite')
    def _onchange_honoraire_inputs(self):
        if self.facture_modele_code == 'honoraires_consultant':
            self._compute_honoraire_lines()
            target_amt = self.honoraire_line_10_net_a_payer or self.honoraire_line_3_total_prestation
            if target_amt > 0:
                lines = self.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                line_name = self.honoraire_objet or _("Prestation intellectuelle / Honoraires de consultation")
                if lines:
                    lines[0].name = line_name
                    lines[0].quantity = self.honoraire_quantite or 1.0
                    lines[0].price_unit = target_amt
                else:
                    self.invoice_line_ids = [(0, 0, {
                        'name': line_name,
                        'quantity': self.honoraire_quantite or 1.0,
                        'price_unit': target_amt,
                    })]

    # --- APERÇU HTML DIRECT DANS LE FORMULAIRE ---
    @api.depends(
        'facture_modele_code',
        'honoraire_line_1_montant',
        'honoraire_line_2_montant',
        'honoraire_line_3_total_prestation',
        'honoraire_line_4_tranche_1_honoraire',
        'honoraire_line_5_tranche_1_frais',
        'honoraire_line_6_total_tranche_1',
        'honoraire_line_7_tranche_2_honoraire',
        'honoraire_line_8_tranche_3_honoraire',
        'honoraire_line_9_retenue_source',
        'honoraire_line_10_net_a_payer',
        'honoraire_net_lettres',
        'honoraire_unite',
        'honoraire_quantite',
        'currency_id'
    )
    def _compute_honoraire_preview_html(self):
        for move in self:
            if move.facture_modele_code != 'honoraires_consultant':
                move.honoraire_preview_html = False
                continue

            curr = move.currency_id.symbol or 'FCFA'
            uom = move.honoraire_unite or ''
            qty = f"{move.honoraire_quantite:g}" if move.honoraire_quantite else "1"

            def fmt(val):
                return move.format_monetary_value(val)

            move.honoraire_preview_html = f"""
            <div class="table-responsive my-3">
                <table class="table table-bordered text-dark" style="border: 2px solid #000; width: 100%; border-collapse: collapse; font-size: 13px; background-color: #fff;">
                    <thead>
                        <tr style="background-color: #f8f9fa; border: 1.5px solid #000; font-weight: bold; text-align: center;">
                            <th style="border: 1.5px solid #000; width: 5%; padding: 6px;">N°</th>
                            <th style="border: 1.5px solid #000; width: 45%; padding: 6px; text-align: left;">Désignations</th>
                            <th style="border: 1.5px solid #000; width: 10%; padding: 6px;">Unité</th>
                            <th style="border: 1.5px solid #000; width: 10%; padding: 6px;">Quantité</th>
                            <th style="border: 1.5px solid #000; width: 15%; padding: 6px;">Prix unitaire TTC</th>
                            <th style="border: 1.5px solid #000; width: 15%; padding: 6px;">Montant TTC</th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- 1. Honoraires des consultants -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">1</td>
                            <td style="border: 1px solid #000; padding: 6px; font-weight: 500;">Honoraires des consultants</td>
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">{uom}</td>
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">{qty}</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px;">{fmt(move.honoraire_line_1_montant)}</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px; font-weight: 600;">{fmt(move.honoraire_line_1_montant)}</td>
                        </tr>
                        <!-- 2. Frais Remboursable -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">2</td>
                            <td style="border: 1px solid #000; padding: 6px;">Frais Remboursable<br/><small class="text-muted">(déplacements, hébergements, rapports et communications 100%)</small></td>
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">{uom}</td>
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">{qty}</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px;">{fmt(move.honoraire_line_2_montant)}</td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px; font-weight: 600;">{fmt(move.honoraire_line_2_montant)}</td>
                        </tr>
                        <!-- 3. Montant total de la prestation -->
                        <tr style="border: 1.5px solid #000; background-color: #f1f3f5; font-weight: bold;">
                            <td style="border: 1.5px solid #000; text-align: center; padding: 6px;">3</td>
                            <td style="border: 1.5px solid #000; padding: 6px;">Montant total de la prestation</td>
                            <td style="border: 1.5px solid #000;"></td>
                            <td style="border: 1.5px solid #000;"></td>
                            <td style="border: 1.5px solid #000;"></td>
                            <td style="border: 1.5px solid #000; text-align: right; padding: 6px;">{fmt(move.honoraire_line_3_total_prestation)}</td>
                        </tr>
                        <!-- 4. Paiement 1ere tranche Avance 30% Honoraire -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">4</td>
                            <td style="border: 1px solid #000; padding: 6px;">Paiement 1ere tranche<br/><small class="text-muted">(Avance {move.honoraire_taux_tranche_1:g}% Honoraire)</small></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px;">{fmt(move.honoraire_line_4_tranche_1_honoraire)}</td>
                        </tr>
                        <!-- 5. Paiement 1ere tranche 100% Frais -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">5</td>
                            <td style="border: 1px solid #000; padding: 6px;">Paiement 1ere tranche (100% Frais remboursable)</td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px;">{fmt(move.honoraire_line_5_tranche_1_frais)}</td>
                        </tr>
                        <!-- 6. Total règlement 1ere Tranche -->
                        <tr style="border: 1.5px solid #000; background-color: #f1f3f5; font-weight: bold;">
                            <td style="border: 1.5px solid #000; text-align: center; padding: 6px;">6</td>
                            <td style="border: 1.5px solid #000; padding: 6px;">Total règlement 1ere Tranche</td>
                            <td style="border: 1.5px solid #000;"></td>
                            <td style="border: 1.5px solid #000;"></td>
                            <td style="border: 1.5px solid #000;"></td>
                            <td style="border: 1.5px solid #000; text-align: right; padding: 6px;">{fmt(move.honoraire_line_6_total_tranche_1)}</td>
                        </tr>
                        <!-- 7. Paiement 2 ème Tranche 30% -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">7</td>
                            <td style="border: 1px solid #000; padding: 6px;">Paiement 2 ème Tranche {move.honoraire_taux_tranche_2:g}%Honoraire<br/><small class="text-muted">(Après 50% de prestation exécutée)</small></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px;">{fmt(move.honoraire_line_7_tranche_2_honoraire)}</td>
                        </tr>
                        <!-- 8. Paiement 3 ème Tranche 40% -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">8</td>
                            <td style="border: 1px solid #000; padding: 6px;">Paiement 3 ème Tranche {move.honoraire_taux_tranche_3:g}%Honoraire<br/><small class="text-muted">(Après 100% de prestation exécutée)</small></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px;">{fmt(move.honoraire_line_8_tranche_3_honoraire)}</td>
                        </tr>
                        <!-- 9. Retenue à la source 5% -->
                        <tr style="border: 1px solid #000;">
                            <td style="border: 1px solid #000; text-align: center; padding: 6px;">9</td>
                            <td style="border: 1px solid #000; padding: 6px;">Retenue à la source ({move.honoraire_taux_retenue:g}% Tranche 1+2+3)</td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000;"></td>
                            <td style="border: 1px solid #000; text-align: right; padding: 6px; color: #b02a37;">{fmt(move.honoraire_line_9_retenue_source)}</td>
                        </tr>
                        <!-- 10. Net à payer Tranche 2+3 (GRISÉ FONCÉ COMME SUR LA PHOTO) -->
                        <tr style="border: 2px solid #000; background-color: #a6a6a6; color: #000; font-weight: bold; font-size: 14px;">
                            <td style="border: 2px solid #000; text-align: center; padding: 8px;">10</td>
                            <td style="border: 2px solid #000; padding: 8px;">Net à payer Tranche 2+3</td>
                            <td style="border: 2px solid #000;"></td>
                            <td style="border: 2px solid #000;"></td>
                            <td style="border: 2px solid #000;"></td>
                            <td style="border: 2px solid #000; text-align: right; padding: 8px;">{fmt(move.honoraire_line_10_net_a_payer)}</td>
                        </tr>
                    </tbody>
                </table>
                <div class="p-2 mt-2 bg-light border text-dark" style="border: 1.5px solid #000 !important; font-size: 13px;">
                    <strong>Arrêtée la présente facture à la somme de :</strong>
                    <span class="text-uppercase fw-bold ms-1">{move.honoraire_net_lettres or ''}</span>
                </div>
            </div>
            """

    # --- DÉLÉGATION D'IMPRESSION DU RAPPORT PDF ---
    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.facture_modele_code == 'honoraires_consultant':
            return 'btp_decompte.report_facture_honoraires_document'
        return super()._get_name_invoice_report()

    def action_print_facture_honoraires(self):
        self.ensure_one()
        return self.env.ref('btp_decompte.action_report_facture_honoraires').report_action(self)

    # --- CREATE & WRITE POUR SYNCHRONISATION SÉCURISÉE ---
    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.facture_modele_code == 'honoraires_consultant' and not self.env.context.get('skip_sync_honoraire'):
                move._compute_honoraire_lines()
                target_amt = move.honoraire_line_10_net_a_payer or move.honoraire_line_3_total_prestation
                lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                if not lines and target_amt > 0:
                    move.with_context(skip_sync_honoraire=True).write({
                        'invoice_line_ids': [(0, 0, {
                            'name': move.honoraire_objet or _("Prestation intellectuelle / Honoraires de consultation"),
                            'quantity': move.honoraire_quantite or 1.0,
                            'price_unit': target_amt,
                        })]
                    })
        return moves

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('skip_sync_honoraire') and any(k in vals for k in ('honoraire_montant', 'honoraire_frais_remboursables', 'honoraire_objet', 'honoraire_quantite')):
            for move in self:
                if move.facture_modele_code == 'honoraires_consultant':
                    move._compute_honoraire_lines()
                    target_amt = move.honoraire_line_10_net_a_payer or move.honoraire_line_3_total_prestation
                    lines = move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))
                    if lines and len(lines) == 1 and target_amt > 0:
                        lines[0].with_context(skip_sync_honoraire=True).write({
                            'price_unit': target_amt,
                            'name': move.honoraire_objet or lines[0].name,
                            'quantity': move.honoraire_quantite or lines[0].quantity or 1.0,
                        })
                    elif not lines and target_amt > 0:
                        move.with_context(skip_sync_honoraire=True).write({
                            'invoice_line_ids': [(0, 0, {
                                'name': move.honoraire_objet or _("Prestation intellectuelle / Honoraires de consultation"),
                                'quantity': move.honoraire_quantite or 1.0,
                                'price_unit': target_amt,
                            })]
                        })
        return res
