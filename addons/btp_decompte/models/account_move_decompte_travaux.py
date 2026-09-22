# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import models, fields, api, _
# pyrefly: ignore [missing-import]
from odoo.exceptions import ValidationError

class AccountMoveDecompteTravaux(models.Model):
    _inherit = 'account.move'

    # --- 1. CHAMPS D'EN-TÊTE ET RENSEIGNEMENTS DU MARCHÉ ---
    decompte_trv_market_id = fields.Many2one(
        'btp.market',
        string='Marché BTP associé',
        help="Sélectionnez un marché existant pour préremplir automatiquement les données et récupérer l'historique des décomptes."
    )
    decompte_trv_numero = fields.Char(
        string='Décompte',
        default='Décompte N° 1',
        tracking=True,
        help="Ex: Décompte N° 1, Décompte N° 2, Décompte N° 3..."
    )
    decompte_trv_objet = fields.Text(
        string='OBJET',
        tracking=True,
        help="Objet des travaux"
    )
    decompte_trv_marche_num = fields.Char(
        string='Marché N°',
        tracking=True,
        help="Ex: N° 2026-088/MID/SG/DGI"
    )
    decompte_trv_financement = fields.Char(
        string='Financement',
        tracking=True,
        help="Ex: Budget de l'État, Fonds propres, etc."
    )
    decompte_trv_city = fields.Char(
        string='Ville de facturation',
        default='Ouagadougou',
        tracking=True
    )
    decompte_trv_signataire_bureau = fields.Char(
        string='Titre signataire Bureau',
        default='Le Bureau'
    )
    decompte_trv_nom_bureau = fields.Char(
        string='Nom / Entreprise signataire Bureau'
    )
    decompte_trv_signataire_mo = fields.Char(
        string='Titre Maître d\'Ouvrage',
        default='Le Maître d\'Ouvrage'
    )
    decompte_trv_nom_mo = fields.Char(
        string='Nom / Structure Maître d\'Ouvrage'
    )

    # --- 2. MONTANTS GLOBAUX DU MARCHÉ ET AVANCEMENT ---
    decompte_trv_montant_marche_ht = fields.Monetary(
        string='Montant total marché en HT',
        currency_field='currency_id',
        tracking=True,
        default=0.0,
        help="Montant contractuel global HT du marché"
    )
    decompte_trv_tva_marche_rate = fields.Float(
        string='Taux TVA Marché (%)',
        default=18.0
    )
    decompte_trv_tva_marche = fields.Monetary(
        string='Montant de la TVA 18%',
        currency_field='currency_id',
        compute='_compute_decompte_trv_marche_totals',
        store=True,
        help="Montant total marché en HT * 18%"
    )
    decompte_trv_montant_marche_ttc = fields.Monetary(
        string='Montant total marché en TTC',
        currency_field='currency_id',
        compute='_compute_decompte_trv_marche_totals',
        store=True,
        help="Montant total marché en HT + Montant de la TVA 18%"
    )
    decompte_trv_avancement_taux = fields.Float(
        string='Avancement (%)',
        digits=(16, 4),
        default=0.0,
        tracking=True,
        help="Taux d'avancement des travaux pour ce décompte (entre 0% et 100%)"
    )

    # --- 3. MONTANT BRUT DU DÉCOMPTE ---
    decompte_trv_montant_cumule_ht = fields.Monetary(
        string='Montant cumulé HT',
        currency_field='currency_id',
        compute='_compute_decompte_trv_values',
        store=True,
        help="Montant total marché HT * Avancement (%)"
    )
    decompte_trv_decomptes_precedents_ht = fields.Monetary(
        string='Décomptes précédents HT',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help="Montant cumulé HT des décomptes précédents (Néant / 0 si premier décompte)"
    )
    decompte_trv_montant_brut = fields.Monetary(
        string='Montant brut du décompte',
        currency_field='currency_id',
        compute='_compute_decompte_trv_values',
        store=True,
        help="Montant brut = Montant cumulé HT - Décomptes précédents HT"
    )

    # --- 4. SECTION RETENUES OPÉRÉES ---
    decompte_trv_avance_percue = fields.Monetary(
        string='Avance de démarrage perçue',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
        help="Montant de l'avance de démarrage perçue (L'avance de démarrage n'est pas un décompte)"
    )
    decompte_trv_taux_garantie = fields.Float(
        string='Taux Retenue de Garantie (%)',
        default=5.0
    )
    decompte_trv_retenue_garantie = fields.Monetary(
        string='Retenue précédente de garantie (5%)',
        currency_field='currency_id',
        compute='_compute_decompte_trv_values',
        store=True,
        help="5% du montant brut du décompte"
    )
    decompte_trv_taux_arcop = fields.Float(
        string='Taux Retenue ARCOP (%)',
        default=0.4
    )
    decompte_trv_retenue_arcop = fields.Monetary(
        string='Autres retenue (ARCOP 0,4%)',
        currency_field='currency_id',
        compute='_compute_decompte_trv_values',
        store=True,
        help="0,4% du montant HTVA du décompte"
    )
    decompte_trv_total_retenues = fields.Monetary(
        string='Total retenues',
        currency_field='currency_id',
        compute='_compute_decompte_trv_values',
        store=True,
        help="Total retenues = Retenue de garantie (5%) + Retenue ARCOP (0,4%)"
    )

    # --- 5. GRILLE FINALE DES CALCULS ---
    decompte_trv_net_htva = fields.Monetary(
        string='Montant net décompte FCFA en HTVA',
        currency_field='currency_id',
        compute='_compute_decompte_trv_values',
        store=True,
        help="Montant brut du décompte - Total retenues"
    )
    decompte_trv_taux_tva = fields.Float(
        string='Taux TVA Décompte (%)',
        default=18.0
    )
    decompte_trv_tva_decompte = fields.Monetary(
        string='Montant de la TVA 18%',
        currency_field='currency_id',
        compute='_compute_decompte_trv_values',
        store=True,
        help="Montant net décompte HTVA * 18%"
    )
    decompte_trv_net_ttc = fields.Monetary(
        string='Montant net décompte FCFA en TTC',
        currency_field='currency_id',
        compute='_compute_decompte_trv_values',
        store=True,
        help="Montant net décompte HTVA + Montant de la TVA 18%"
    )
    decompte_trv_taux_impot = fields.Float(
        string='Taux Retenue Impôt (%)',
        default=5.0
    )
    decompte_trv_retenue_impot_5 = fields.Monetary(
        string='Retenue de 5% pour impôt sur montant net décompte',
        currency_field='currency_id',
        compute='_compute_decompte_trv_values',
        store=True,
        help="5% pour impôt sur le montant net du décompte HTVA"
    )
    decompte_trv_net_a_payer = fields.Monetary(
        string='NET A PAYER',
        currency_field='currency_id',
        compute='_compute_decompte_trv_values',
        store=True,
        help="NET A PAYER = Montant net TTC - Retenue de 5% pour impôt"
    )
    decompte_trv_net_lettres = fields.Char(
        string='Arrêté le présent paiement à la somme de',
        compute='_compute_decompte_trv_values',
        store=True
    )
    decompte_trv_preview_html = fields.Html(
        string='Aperçu Document Décompte Travaux BTP',
        compute='_compute_decompte_trv_preview_html'
    )

    # --- VALIDATIONS ANTI-ERREURS ---
    @api.constrains(
        'decompte_trv_montant_marche_ht',
        'decompte_trv_avancement_taux',
        'decompte_trv_decomptes_precedents_ht',
        'decompte_trv_avance_percue'
    )
    def _check_decompte_trv_inputs(self):
        for move in self:
            if move.facture_modele_code == 'decompte_travaux_btp':
                if move.decompte_trv_montant_marche_ht < 0:
                    raise ValidationError(_("Le montant total du marché en HT ne peut pas être négatif."))
                if move.decompte_trv_avancement_taux < 0 or move.decompte_trv_avancement_taux > 100:
                    raise ValidationError(_("Le taux d'avancement doit être compris entre 0%% et 100%%."))
                if move.decompte_trv_decomptes_precedents_ht < 0:
                    raise ValidationError(_("Le montant des décomptes précédents ne peut pas être négatif."))
                if move.decompte_trv_avance_percue < 0:
                    raise ValidationError(_("L'avance de démarrage perçue ne peut pas être négative."))

    # --- ONCHANGE LORS DE LA SÉLECTION D'UN MARCHÉ ---
    @api.onchange('decompte_trv_market_id')
    def _onchange_decompte_trv_market_id(self):
        if self.decompte_trv_market_id:
            m = self.decompte_trv_market_id
            if m.partner_id:
                self.partner_id = m.partner_id
            if m.objet:
                self.decompte_trv_objet = m.objet
            if m.name:
                self.decompte_trv_marche_num = m.name
            if m.financement:
                self.decompte_trv_financement = m.financement
            if m.amount_untaxed:
                self.decompte_trv_montant_marche_ht = m.amount_untaxed
            if m.advance_total:
                self.decompte_trv_avance_percue = m.advance_total

            # Récupérer l'historique des décomptes précédents du même marché
            prev_moves = self.env['account.move'].search([
                ('decompte_trv_market_id', '=', m.id),
                ('facture_modele_code', '=', 'decompte_travaux_btp'),
                ('id', '!=', self._origin.id if self._origin else False),
                ('state', '!=', 'cancel'),
            ], order='invoice_date asc, id asc')

            if prev_moves:
                self.decompte_trv_decomptes_precedents_ht = sum(prev_moves.mapped('decompte_trv_montant_brut'))
                self.decompte_trv_numero = _('Décompte N° %s') % (len(prev_moves) + 1)
            else:
                self.decompte_trv_decomptes_precedents_ht = 0.0
                self.decompte_trv_numero = _('Décompte N° 1')

    # --- CALCUL DU MARCHÉ HT, TVA 18%, ET MARCHÉ TTC ---
    @api.depends('facture_modele_code', 'decompte_trv_montant_marche_ht', 'decompte_trv_tva_marche_rate', 'currency_id')
    def _compute_decompte_trv_marche_totals(self):
        for move in self:
            if move.facture_modele_code != 'decompte_travaux_btp':
                continue
            curr = move.currency_id
            def round_val(v):
                return curr.round(v) if curr else round(v, 2)

            mht = move.decompte_trv_montant_marche_ht or 0.0
            tva_rate = (move.decompte_trv_tva_marche_rate or 18.0) / 100.0
            tva_amount = mht * tva_rate
            move.decompte_trv_tva_marche = round_val(tva_amount)
            move.decompte_trv_montant_marche_ttc = round_val(mht + tva_amount)

    # --- CALCULS PRINCIPAUX SELON LE MODÈLE DÉCOMPTE DE TRAVAUX BTP ---
    @api.depends(
        'facture_modele_code',
        'decompte_trv_montant_marche_ht',
        'decompte_trv_avancement_taux',
        'decompte_trv_decomptes_precedents_ht',
        'decompte_trv_taux_garantie',
        'decompte_trv_taux_arcop',
        'decompte_trv_taux_tva',
        'decompte_trv_taux_impot',
        'currency_id'
    )
    def _compute_decompte_trv_values(self):
        for move in self:
            if move.facture_modele_code != 'decompte_travaux_btp':
                continue

            curr = move.currency_id
            def round_val(v):
                return curr.round(v) if curr else round(v, 2)

            mht = move.decompte_trv_montant_marche_ht or 0.0
            taux_av = (move.decompte_trv_avancement_taux or 0.0) / 100.0
            prec_ht = move.decompte_trv_decomptes_precedents_ht or 0.0

            # 1. Montant cumulé HT = Montant total marché en HT * Avancement
            cumul_ht = mht * taux_av
            move.decompte_trv_montant_cumule_ht = round_val(cumul_ht)

            # 2. Montant brut du décompte = Montant cumulé HT - Décomptes précédents HT
            brut = max(0.0, cumul_ht - prec_ht)
            move.decompte_trv_montant_brut = round_val(brut)

            # 3. Retenue précédente de garantie = 5% du montant brut
            garantie_rate = (move.decompte_trv_taux_garantie or 5.0) / 100.0
            ret_garantie = brut * garantie_rate
            move.decompte_trv_retenue_garantie = round_val(ret_garantie)

            # 4. Autres retenue (ARCOP 0,4% du montant HTVA du décompte)
            arcop_rate = (move.decompte_trv_taux_arcop or 0.4) / 100.0
            ret_arcop = brut * arcop_rate
            move.decompte_trv_retenue_arcop = round_val(ret_arcop)

            # 5. Total retenues = Retenue garantie + Retenue ARCOP
            tot_ret = ret_garantie + ret_arcop
            move.decompte_trv_total_retenues = round_val(tot_ret)

            # 6. Montant net décompte FCFA en HTVA = Montant brut du décompte - Total retenues
            net_htva = max(0.0, brut - tot_ret)
            move.decompte_trv_net_htva = round_val(net_htva)

            # 7. Montant de la TVA 18% = Net HTVA * 18%
            tva_rate = (move.decompte_trv_taux_tva or 18.0) / 100.0
            tva_val = net_htva * tva_rate
            move.decompte_trv_tva_decompte = round_val(tva_val)

            # 8. Montant net décompte FCFA en TTC = Net HTVA + TVA
            net_ttc = net_htva + tva_val
            move.decompte_trv_net_ttc = round_val(net_ttc)

            # 9. Retenue de 5% pour impôt sur montant net décompte = Net HTVA * 5%
            impot_rate = (move.decompte_trv_taux_impot or 5.0) / 100.0
            ret_impot = net_htva * impot_rate
            move.decompte_trv_retenue_impot_5 = round_val(ret_impot)

            # 10. NET A PAYER = Net TTC - Retenue Impôt 5%
            net_a_payer = max(0.0, net_ttc - ret_impot)
            move.decompte_trv_net_a_payer = round_val(net_a_payer)

            # 11. Arrêté en toutes lettres
            curr_label = curr.currency_unit_label if curr and curr.currency_unit_label else 'Franc CFA'
            move.decompte_trv_net_lettres = self._convert_amount_to_french_words(net_a_payer, curr_label)

    # --- CONVERSION EN TOUTES LETTRES ---
    def _convert_amount_to_french_words(self, amount, currency_name="Franc CFA"):
        try:
            int_amount = int(round(amount))
            if int_amount == 0:
                return f"Zéro ({currency_name})"
            words = self._num_to_words_fr(int_amount)
            return f"{words.capitalize()} ({currency_name})"
        except Exception:
            return f"{amount:,.0f} {currency_name}"

    def _num_to_words_fr(self, n):
        units = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
                 "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept",
                 "dix-huit", "dix-neuf"]
        tens = ["", "", "vingt", "trente", "quarante", "cinquante", "soixante", "soixante-dix",
                "quatre-vingt", "quatre-vingt-dix"]

        if n < 0:
            return "moins " + self._num_to_words_fr(-n)
        if n == 0:
            return "zéro"
        if n < 20:
            return units[n]
        if n < 70:
            rem = n % 10
            t = tens[n // 10]
            if rem == 1:
                return f"{t} et un"
            elif rem > 1:
                return f"{t}-{units[rem]}"
            return t
        if n < 80:
            rem = n - 60
            if rem == 11:
                return "soixante et onze"
            return f"soixante-{units[rem]}"
        if n < 100:
            rem = n - 80
            if rem == 0:
                return "quatre-vingts"
            return f"quatre-vingt-{units[rem]}"
        if n < 1000:
            h = n // 100
            rem = n % 100
            h_str = "cent" if h == 1 else f"{units[h]} cent"
            if h > 1 and rem == 0:
                h_str += "s"
            if rem > 0:
                return f"{h_str} {self._num_to_words_fr(rem)}"
            return h_str
        if n < 1000000:
            th = n // 1000
            rem = n % 1000
            th_str = "mille" if th == 1 else f"{self._num_to_words_fr(th)} mille"
            if rem > 0:
                return f"{th_str} {self._num_to_words_fr(rem)}"
            return th_str
        if n < 1000000000:
            m = n // 1000000
            rem = n % 1000000
            m_str = "un million" if m == 1 else f"{self._num_to_words_fr(m)} millions"
            if rem > 0:
                return f"{m_str} {self._num_to_words_fr(rem)}"
            return m_str
        bill = n // 1000000000
        rem = n % 1000000000
        b_str = "un milliard" if bill == 1 else f"{self._num_to_words_fr(bill)} milliards"
        if rem > 0:
            return f"{b_str} {self._num_to_words_fr(rem)}"
        return b_str

    # --- APERÇU HTML EN TEMPS RÉEL DU DÉCOMPTE ---
    @api.depends(
        'facture_modele_code',
        'decompte_trv_numero',
        'decompte_trv_objet',
        'decompte_trv_marche_num',
        'decompte_trv_financement',
        'decompte_trv_montant_marche_ht',
        'decompte_trv_tva_marche',
        'decompte_trv_montant_marche_ttc',
        'decompte_trv_avancement_taux',
        'decompte_trv_montant_brut',
        'decompte_trv_avance_percue',
        'decompte_trv_decomptes_precedents_ht',
        'decompte_trv_retenue_garantie',
        'decompte_trv_retenue_arcop',
        'decompte_trv_total_retenues',
        'decompte_trv_net_htva',
        'decompte_trv_tva_decompte',
        'decompte_trv_net_ttc',
        'decompte_trv_retenue_impot_5',
        'decompte_trv_net_a_payer',
        'currency_id'
    )
    def _compute_decompte_trv_preview_html(self):
        for move in self:
            if move.facture_modele_code != 'decompte_travaux_btp':
                move.decompte_trv_preview_html = False
                continue

            curr = move.currency_id.symbol if move.currency_id else 'FCFA'
            def fmt(val):
                return f"{val:,.0f} {curr}".replace(',', ' ')

            precedents_label = "Néant; l'avance de démarrage n'est pas un décompte"
            if move.decompte_trv_decomptes_precedents_ht > 0:
                precedents_val_str = fmt(move.decompte_trv_decomptes_precedents_ht)
            else:
                precedents_val_str = "Néant"

            sign_bureau = move.decompte_trv_signataire_bureau or 'Le Bureau'
            sign_mo = move.decompte_trv_signataire_mo or "Le Maître d'Ouvrage"

            html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 11.5px; border: 1px solid #ccc; padding: 18px; background: #fff; max-width: 780px; margin: auto; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <div style="text-align: right; margin-bottom: 12px; font-weight: bold; color: #444;">
                    {move.decompte_trv_city or 'Ouagadougou'}, le : {fields.Date.today().strftime('%d/%m/%Y')}
                </div>
                <div style="text-align: center; font-size: 15px; font-weight: bold; text-decoration: underline; margin-bottom: 16px;">
                    FACTURE N° : {move.name or 'BROUILLON'}
                </div>
                
                <table style="width: 100%; margin-bottom: 15px; font-size: 11px; line-height: 1.5;">
                    <tr><td style="width: 35%; font-weight: bold; text-decoration: underline;">OBJET :</td><td>{move.decompte_trv_objet or '-'}</td></tr>
                    <tr><td style="font-weight: bold; text-decoration: underline;">Doit :</td><td>{move.partner_id.name if move.partner_id else '-'}</td></tr>
                    <tr><td style="font-weight: bold;">Marché N° :</td><td>{move.decompte_trv_marche_num or '-'}</td></tr>
                    <tr><td>Financement :</td><td>{move.decompte_trv_financement or '-'}</td></tr>
                    <tr><td>Décompte :</td><td style="font-weight: bold; color: #0275d8;">{move.decompte_trv_numero or 'Décompte N° 1'}</td></tr>
                    <tr><td>Montant total marché en HT :</td><td style="font-weight: bold;">{fmt(move.decompte_trv_montant_marche_ht)}</td></tr>
                    <tr><td>Montant de la TVA 18% :</td><td>{fmt(move.decompte_trv_tva_marche)}</td></tr>
                    <tr><td>Montant total marché en TTC :</td><td style="font-weight: bold;">{fmt(move.decompte_trv_montant_marche_ttc)}</td></tr>
                    <tr><td>Avancement :</td><td style="font-weight: bold; color: #5cb85c;">{move.decompte_trv_avancement_taux:.2f} %</td></tr>
                </table>

                <!-- MONTANT BRUT AVEC CADRE DOUBLE BORDURE -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 2px solid #333; padding-bottom: 8px;">
                    <div style="font-weight: bold; font-size: 12.5px; text-decoration: underline;">Montant brut du décompte :</div>
                    <div style="border: 3px double #000; padding: 4px 18px; font-size: 13.5px; font-weight: bold; min-width: 130px; text-align: right; background: #fafafa;">
                        {fmt(move.decompte_trv_montant_brut)}
                    </div>
                </div>

                <!-- SECTION RETENUES OPÉRÉES -->
                <div style="margin-bottom: 14px;">
                    <div style="font-weight: bold; font-size: 12px; text-decoration: underline; margin-bottom: 6px;">Retenues opérées :</div>
                    <table style="width: 100%; border-collapse: collapse; border: 1px solid #000;">
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 5px; width: 75%;">Avance de démarrage perçue :</td>
                            <td style="padding: 5px; width: 25%; text-align: right; border-left: 1px solid #000; font-weight: bold;">{fmt(move.decompte_trv_avance_percue)}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 5px;">Décomptes précédents perçus : <span style="font-style: italic; color: #555;">({precedents_label})</span></td>
                            <td style="padding: 5px; text-align: right; border-left: 1px solid #000;">{precedents_val_str}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 5px;">Retenue précédente de garantie : <span style="font-style: italic;">(5% du montant brut du décompte)</span></td>
                            <td style="padding: 5px; text-align: right; border-left: 1px solid #000; font-weight: bold; color: #d9534f;">{fmt(move.decompte_trv_retenue_garantie)}</td>
                        </tr>
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 5px;">Autres retenue <span style="font-style: italic;">(ARCOP 0,4% du montant HTVA du décompte)</span></td>
                            <td style="padding: 5px; text-align: right; border-left: 1px solid #000; font-weight: bold; color: #d9534f;">{fmt(move.decompte_trv_retenue_arcop)}</td>
                        </tr>
                        <tr style="background: #f8f9fa; font-weight: bold;">
                            <td style="padding: 6px; text-align: right; text-decoration: underline;">Total retenues :</td>
                            <td style="padding: 6px; text-align: right; border-left: 1px solid #000; color: #d9534f;">{fmt(move.decompte_trv_total_retenues)}</td>
                        </tr>
                    </table>
                </div>

                <!-- GRILLE FINALE DES CALCULS -->
                <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; margin-bottom: 16px;">
                    <tr style="border-bottom: 1px solid #000;">
                        <td style="padding: 6px; width: 75%; font-weight: bold;">Montant net décompte FCFA en HTVA :</td>
                        <td style="padding: 6px; width: 25%; text-align: right; border-left: 1px solid #000; font-weight: bold; color: #0275d8;">{fmt(move.decompte_trv_net_htva)}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #000;">
                        <td style="padding: 6px; font-weight: bold;">Montant de la TVA 18% :</td>
                        <td style="padding: 6px; text-align: right; border-left: 1px solid #000;">{fmt(move.decompte_trv_tva_decompte)}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #000; background: #eef7fb;">
                        <td style="padding: 6px; font-weight: bold;">Montant net décompte FCFA en TTC :</td>
                        <td style="padding: 6px; text-align: right; border-left: 1px solid #000; font-weight: bold; font-size: 12px; color: #0275d8;">{fmt(move.decompte_trv_net_ttc)}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #000;">
                        <td style="padding: 6px;">Retenue de 5% pour impôt sur montant net décompte :</td>
                        <td style="padding: 6px; text-align: right; border-left: 1px solid #000; font-weight: bold; color: #d9534f;">{fmt(move.decompte_trv_retenue_impot_5)}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #000;">
                        <td style="padding: 6px;">Retenue ARCOP de 0,4% :</td>
                        <td style="padding: 6px; text-align: right; border-left: 1px solid #000; font-weight: bold; color: #d9534f;">{fmt(move.decompte_trv_retenue_arcop)}</td>
                    </tr>
                    <tr style="background: #2c3e50; color: #fff; font-weight: bold; font-size: 12.5px;">
                        <td style="padding: 8px; text-align: center; letter-spacing: 1px;">NET A PAYER</td>
                        <td style="padding: 8px; text-align: right; border-left: 1px solid #fff; font-size: 13.5px;">{fmt(move.decompte_trv_net_a_payer)}</td>
                    </tr>
                </table>

                <div style="font-size: 10.5px; margin-bottom: 35px;">
                    <strong>Arrêté le présent paiement à la somme de : </strong>{move.decompte_trv_net_lettres or ''}
                </div>

                <div style="display: flex; justify-content: space-between; padding: 0 30px;">
                    <div style="font-weight: bold; text-decoration: underline;">{sign_bureau}</div>
                    <div style="font-weight: bold; text-decoration: underline;">{sign_mo}</div>
                </div>
            </div>
            """
            move.decompte_trv_preview_html = html

    # --- SYNCHRONISATION COMPTABLE ET POSTING ---
    def action_post(self):
        for move in self:
            if move.facture_modele_code == 'decompte_travaux_btp' and move.move_type == 'out_invoice':
                move._sync_decompte_trv_accounting_lines()
        return super().action_post()

    def _sync_decompte_trv_accounting_lines(self):
        self.ensure_one()
        net_ht = self.decompte_trv_net_htva or self.decompte_trv_montant_brut
        if net_ht <= 0:
            return

        line_desc = f"{self.decompte_trv_numero or 'Décompte'} - {self.decompte_trv_objet or 'Travaux BTP'}"
        existing_line = self.invoice_line_ids.filtered(lambda l: not l.display_type)
        if existing_line:
            existing_line[0].write({
                'name': line_desc,
                'quantity': 1.0,
                'price_unit': net_ht,
            })
        else:
            default_account = self.journal_id.default_account_id
            if not default_account:
                accounts = self.env['account.account'].search([
                    ('account_type', '=', 'income'),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
                default_account = accounts[0] if accounts else False

            line_vals = {
                'move_id': self.id,
                'name': line_desc,
                'quantity': 1.0,
                'price_unit': net_ht,
            }
            if default_account:
                line_vals['account_id'] = default_account.id
            self.env['account.move.line'].create(line_vals)

    # --- ACTION D'IMPRESSION DU RAPPORT DÉDIÉ ---
    def action_print_decompte_travaux(self):
        self.ensure_one()
        return self.env.ref('btp_decompte.action_report_decompte_travaux').report_action(self)

    def _get_name_invoice_report(self):
        if self.facture_modele_code == 'decompte_travaux_btp':
            return 'btp_decompte.report_decompte_travaux_template'
        return super()._get_name_invoice_report()
