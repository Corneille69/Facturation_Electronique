# Module Odoo 17 : Facturation Électronique & BTP (Décomptes, Petits Marchés et Modèles de Factures)

Ce projet est une solution complète et modulaire de **Facturation Électronique et Gestion BTP** pour **Odoo 17 Community & Enterprise**, conçue selon les spécifications financières et comptables officielles.

---

## 🏗️ Architecture Fonctionnelle

Le module `btp_decompte` s'intègre nativement avec les modules standards d'Odoo (**Contacts `res.partner`**, **Factures `account.move`** et la comptabilité générale).

### 1. Modèles de Factures Spécifiques (Galerie Visuelle)
- **Choix visuel du modèle** : Guidage de l'utilisateur avec prévisualisation fidèle par image du document tel qu'il sera imprimé.
- **Modèle Bordereau de Travaux & Déduction Acompte** :
  - Saisie du Montant Principal HT ou Montant HT du Marché (synchronisation bidirectionnelle automatique).
  - Déduction Facture N°1 perçue de 50% (affichée avec le signe négatif `-`).
  - Calculs instantanés en temps réel : Net HT, TVA 18%, Net TTC (#9ab7d9) et arrêté en toutes lettres (Francs CFA).
  - QR Code officiel et impression PDF officielle personnalisée.
  - Évolutif : Architecture prête pour accueillir de nouveaux types et modèles de factures à l'avenir.

### 2. Petits Marchés BTP (Sans Décompte)
- Gestion simplifiée pour les petits marchés de travaux :
  - Montant HT, TVA 18 %, Montant TTC.
  - Taux d'avance de démarrage (0 à 30%).
  - Facture d'avance générée en un clic avec tableau récapitulatif financier officiel (7 lignes).
  - **Strictement aucun système de décompte**.

### 3. Grands Marchés BTP (Avec Décomptes A à Q)
- Gestion complète des marchés publics et privés d'envergure :
  - Enregistrement des marchés et suivi contractuel.
  - Cycle de décomptes successifs (provisoires et définitif).
  - Tableau financier officiel complet de A à Q (Travaux cumulés, remboursement avance, retenue de garantie 5 %, TVA 18 %, net à payer).
  - Traçabilité et historique d'approbation.

---

## 🚀 Démarrage Rapide avec Docker

Le projet inclut la pile complète Odoo 17 et PostgreSQL 16 dans le fichier `compose.yml`.

### Prérequis
- Docker et Docker Compose installés.

### Lancement
```bash
# Démarrer les conteneurs en arrière-plan
docker compose up -d

# Vérifier l'état des services
docker compose ps
```

Accédez à l'application dans votre navigateur :
**http://localhost:8070**

---

## 📁 Structure du Répertoire

```
Facturation_Electronique/
├── compose.yml                     # Configuration Docker Compose (Odoo 17 + DB)
├── README.md                       # Documentation du projet
├── .gitignore                      # Exclusions Git standards
└── addons/
    └── btp_decompte/               # Module Odoo personnalisé
        ├── __manifest__.py         # Manifeste Odoo 17
        ├── __init__.py
        ├── models/                 # Modèles Python ORM
        │   ├── account_move.py
        │   ├── btp_decompte.py
        │   ├── btp_facture_modele.py
        │   ├── btp_market.py
        │   ├── btp_petit_marche.py
        │   ├── res_company.py
        │   ├── res_config_settings.py
        │   └── res_currency.py
        ├── views/                  # Vues XML (Form, Tree, Kanban, Menus)
        │   ├── account_move_views.xml
        │   ├── btp_decompte_views.xml
        │   ├── btp_facture_modele_views.xml
        │   ├── btp_market_views.xml
        │   ├── btp_petit_marche_views.xml
        │   ├── res_company_views.xml
        │   ├── res_config_settings_views.xml
        │   └── menus.xml
        ├── report/                 # Rapports QWeb PDF officiels
        │   ├── btp_decompte_report.xml
        │   ├── btp_decompte_template.xml
        │   ├── btp_facture_bordereau_report.xml
        │   ├── btp_facture_bordereau_template.xml
        │   ├── btp_petit_marche_report.xml
        │   └── btp_petit_marche_template.xml
        ├── data/                   # Données initiales et séquences
        ├── security/               # Règles d'accès et droits (ACL)
        ├── static/                 # Images des modèles, icônes et styles
        └── tests/                  # Tests unitaires et validation complète
```

---

## 🧪 Tests Unitaires & Validation

Des tests automatisés valident l'intégralité du workflow :
```bash
docker compose exec odoo python3 -c "import odoo; odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf']); from odoo.addons.btp_decompte.tests.test_facture_bordereau import run_test; run_test()"
```

---

## 👤 Auteur
- **Corneille69** (https://github.com/Corneille69)
