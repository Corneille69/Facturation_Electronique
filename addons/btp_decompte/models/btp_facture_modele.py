# -*- coding: utf-8 -*-
import base64
import os
# pyrefly: ignore [missing-import]
from odoo import models, fields, api, _

class BtpFactureModele(models.Model):
    _name = 'btp.facture.modele'
    _description = 'Modèle de Facture'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Nom du Modèle', required=True)
    code = fields.Char(string='Code Technique', required=True, index=True)
    sequence = fields.Integer(string='Séquence', default=10)
    description = fields.Text(string='Description & Guide d\'Utilisation')
    image_preview = fields.Binary(string='Image Miniature du Modèle', attachment=True)
    
    # Paramètres par défaut personnalisables
    city_default = fields.Char(string='Ville par défaut', default='Ouagadougou')
    deduction_label_default = fields.Char(
        string='Libellé Déduction Facture N°1',
        default='Montant de la facture n°1 perçue de 50%'
    )
    deduction_rate_default = fields.Float(string='Taux Déduction Défaut (%)', default=50.0)
    signatory_default = fields.Char(string='Titre Signataire', default='Signataire')
    is_default = fields.Boolean(string='Modèle par défaut', default=False)
    active = fields.Boolean(string='Actif', default=True)
    invoice_count = fields.Integer(string='Nombre de factures', compute='_compute_invoice_count')

    def _compute_invoice_count(self):
        for rec in self:
            if rec.code == 'petit_marche':
                rec.invoice_count = self.env['btp.petit.marche'].search_count([])
            elif rec.code == 'grand_marche':
                rec.invoice_count = self.env['btp.decompte'].search_count([])
            else:
                rec.invoice_count = self.env['account.move'].search_count([('facture_modele_id', '=', rec.id)])

    def action_create_invoice(self):
        self.ensure_one()
        if self.code == 'petit_marche':
            return {
                'name': _("Nouveau Petit Marché — Facture d'Avance"),
                'type': 'ir.actions.act_window',
                'res_model': 'btp.petit.marche',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
                'context': {
                    'default_company_id': self.env.company.id,
                }
            }
        elif self.code == 'grand_marche':
            return {
                'name': _("Nouveau Décompte — Grand Marché BTP"),
                'type': 'ir.actions.act_window',
                'res_model': 'btp.decompte',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'current',
                'context': {
                    'default_company_id': self.env.company.id,
                }
            }
        return {
            'name': _('Nouvelle Facture - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'context': {
                'default_move_type': 'out_invoice',
                'default_facture_modele_id': self.id,
                'default_facture_city': self.city_default or 'Ouagadougou',
                'default_facture_deduction_label': self.deduction_label_default or 'Montant de la facture n°1 perçue de 50%',
                'default_facture_deduction_rate': self.deduction_rate_default or 50.0,
                'default_facture_signatory': self.signatory_default or 'Signataire',
                'default_decompte_btp_city': self.city_default or 'Ouagadougou',
                'default_decompte_btp_signataire_titre': self.signatory_default or 'Le Bureau',
                'default_decompte_trv_city': self.city_default or 'Ouagadougou',
                'default_decompte_trv_signataire_bureau': self.signatory_default or 'Le Bureau',
            }
        }

    def action_view_invoices(self):
        self.ensure_one()
        if self.code == 'petit_marche':
            return {
                'name': _("Petits Marchés — Factures d'Avance"),
                'type': 'ir.actions.act_window',
                'res_model': 'btp.petit.marche',
                'view_mode': 'tree,form',
                'target': 'current',
            }
        elif self.code == 'grand_marche':
            return {
                'name': _("Décomptes Grands Marchés BTP"),
                'type': 'ir.actions.act_window',
                'res_model': 'btp.decompte',
                'view_mode': 'tree,form',
                'target': 'current',
            }
        return {
            'name': _('Factures - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('facture_modele_id', '=', self.id)],
            'context': {'default_move_type': 'out_invoice', 'default_facture_modele_id': self.id},
        }


    @api.model
    def _init_default_models(self):
        """Initialisation automatique des modèles avec leurs images de prévisualisation"""
        module_path = os.path.dirname(os.path.dirname(__file__))
        img_dir = os.path.join(module_path, 'static', 'src', 'img')

        def load_img(fname):
            fpath = os.path.join(img_dir, fname)
            if os.path.exists(fpath):
                with open(fpath, 'rb') as f:
                    return base64.b64encode(f.read())
            return False

        models_data = [
            {
                'code': 'bordereau_travaux',
                'name': 'Modèle Bordereau Travaux & Déduction Acompte',
                'sequence': 1,
                'description': 'Facture spécifique avec tableau de travaux (Unité, Quantité, Montant Marché HT, Montant Présente Facture), déduction de facture antérieure (50%), net HT, TVA 18%, net TTC et arrêté en toutes lettres.',
                'image_preview': load_img('modele_bordereau_travaux.png'),
                'city_default': 'Ouagadougou',
                'deduction_label_default': 'Montant de la facture n°1 perçue de 50%',
                'deduction_rate_default': 50.0,
                'signatory_default': 'Signataire',
                'is_default': True,
            },
            {
                'code': 'grand_marche',
                'name': 'Modèle Grand Marché BTP (Décompte A à Q)',
                'sequence': 2,
                'description': 'Facture officielle de Décompte pour les Grands Marchés BTP avec tableau détaillé de A à Q (avancement des travaux, remboursement d’avance, retenue de garantie 5%, retenue à la source 1% et Net à Payer).',
                'image_preview': load_img('modele_grand_marche.png'),
                'city_default': 'Ouagadougou',
                'signatory_default': 'Pour l’Entreprise',
            },
            {
                'code': 'petit_marche',
                'name': 'Modèle Petit Marché BTP (Facture Avance 7 Lignes)',
                'sequence': 3,
                'description': 'Facture d’avance directe pour les Petits Marchés BTP sans décompte, avec tableau des 7 éléments financiers officiels et Code QR de certification.',
                'image_preview': load_img('modele_petit_marche.png'),
                'city_default': 'Ouagadougou',
                'signatory_default': 'Pour l’Entreprise',
            },
            {
                'code': 'honoraires_consultant',
                'name': 'Facture Honoraires / Consultant',
                'sequence': 4,
                'description': 'Facture officielle pour honoraires d’experts et consultants avec tableau des 10 lignes métier, calcul automatique des 3 tranches (30%, 30%, 40%), frais remboursables 100% et retenue à la source 5%.',
                'image_preview': load_img('modele_honoraires_consultant.png'),
                'city_default': 'Ouagadougou',
                'signatory_default': 'Signataire',
            },
            {
                'code': 'honoraires_etudes',
                'name': 'Facture BTP — Honoraires / Études',
                'sequence': 5,
                'description': 'Facture officielle pour études et ingénierie BTP structurée en 3 sections (I. Honoraires, II. Frais Remboursable, III. Frais Divers), calcul automatique des sous-totaux, TVA 18% et Net à Payer.',
                'image_preview': load_img('modele_honoraires_etudes.png'),
                'city_default': 'Ouagadougou',
                'signatory_default': 'Le Bureau',
            },
            {
                'code': 'decompte_btp',
                'name': 'Décompte BTP',
                'sequence': 6,
                'description': 'Facture officielle de décompte BTP avec tableau à 2 colonnes (Désignation / Montant), calcul automatique des formules A à TR, avance 20%, retenue 5%, ARCOP 0,4%, TVA 18% et Net TTC.',
                'image_preview': load_img('modele_decompte_btp.png'),
                'city_default': 'Ouagadougou',
                'signatory_default': 'Le Bureau',
            },
            {
                'code': 'decompte_travaux_btp',
                'name': 'Décompte de travaux BTP',
                'sequence': 7,
                'description': 'Facture officielle de Décompte de travaux BTP conforme au modèle officiel : montant brut, encadré des retenues opérées (avance, décomptes précédents ou néant, retenue garantie 5%, ARCOP 0,4%), Net HTVA, TVA 18%, Net TTC, retenue impôt 5% et NET A PAYER.',
                'image_preview': load_img('modele_decompte_travaux_btp.png'),
                'city_default': 'Ouagadougou',
                'signatory_default': 'Le Bureau',
            },
        ]

        # Suppression des modèles indésirables ou de test de la galerie
        unwanted = self.search([
            '|', '|',
            ('code', 'in', ['standard', 'fjbi']),
            ('name', 'ilike', 'esrtdyfugi%'),
            ('name', 'ilike', '%Standard%')
        ])
        if unwanted:
            unwanted.unlink()

        for m_data in models_data:
            existing = self.search([('code', '=', m_data['code'])], limit=1)
            vals = {
                'name': m_data['name'],
                'sequence': m_data['sequence'],
                'description': m_data['description'],
                'city_default': m_data['city_default'],
                'signatory_default': m_data['signatory_default'],
            }
            if m_data.get('image_preview'):
                vals['image_preview'] = m_data['image_preview']
            if 'deduction_label_default' in m_data:
                vals['deduction_label_default'] = m_data['deduction_label_default']
            if 'deduction_rate_default' in m_data:
                vals['deduction_rate_default'] = m_data['deduction_rate_default']
            if 'is_default' in m_data:
                vals['is_default'] = m_data['is_default']

            if existing:
                existing.write(vals)
            else:
                self.create(m_data)

        # Rendre les pièces jointes des aperçus publiques pour affichage direct et fluide dans la galerie
        self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'btp.facture.modele'),
            ('res_field', '=', 'image_preview')
        ]).write({'public': True})

