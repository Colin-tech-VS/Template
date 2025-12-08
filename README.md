# Template Artworksdigital

**Version :** 1.0 (Corrigée et optimisée)  
**Date :** 2025-12-07  
**Hébergeur :** Scalingo  
**Base de données :** Supabase (PostgreSQL)  
**Dashboard :** admin.artworksdigital.fr

---

## 📋 Description

Ce projet est un **template e-commerce** pour artistes, permettant de :

- 🎨 Afficher et vendre des peintures
- 📦 Gérer les commandes et les clients
- 🛒 Panier et paiement Stripe
- 📧 Notifications par email
- 🎯 Demandes de commandes personnalisées
- 📊 Tableau de bord administrateur
- 🔗 API d'export des données vers le dashboard central

---

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.11+
- PostgreSQL/Supabase
- Scalingo CLI
- Stripe API keys

### Installation Locale

```bash
# Cloner le projet
git clone https://github.com/artworksdigital/template.git
cd template

# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos valeurs

# Démarrer l'application
python app.py
```

L'application sera disponible à `http://localhost:5000`

---

## 🔧 Configuration

### Variables d'Environnement Requises

```bash
# Base de données Supabase
DATABASE_URL=postgresql://user:password@host:5432/database

# Clé API maître
TEMPLATE_MASTER_API_KEY=your-master-key-here

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
```

Voir `.env.example` pour la liste complète.

---

## 📚 Documentation

### Guides Disponibles

1. **[CORRECTIONS_APPLIED.md](./CORRECTIONS_APPLIED.md)** - Corrections et optimisations appliquées
2. **[SUPABASE_SETUP.md](./SUPABASE_SETUP.md)** - Configuration Supabase et Scalingo
3. **[API_INTEGRATION.md](./API_INTEGRATION.md)** - Intégration API avec le dashboard

### Structure du Projet

```
├── app.py                 # Application Flask principale
├── database.py            # Gestion de la base de données PostgreSQL
├── requirements.txt       # Dépendances Python
├── Procfile              # Configuration Scalingo
├── .env.example          # Variables d'environnement (exemple)
├── templates/            # Templates HTML
│   ├── admin/            # Pages administrateur
│   └── ...               # Pages publiques
├── static/               # Fichiers statiques
│   ├── Images/           # Images des peintures
│   ├── js/               # JavaScript
│   └── style.css         # Feuille de style
└── docs/                 # Documentation
    ├── CORRECTIONS_APPLIED.md
    ├── SUPABASE_SETUP.md
    └── API_INTEGRATION.md
```

---

## 🌐 Routes Principales

### Routes Publiques

| Route | Description |
|-------|-------------|
| `/` | Accueil |
| `/boutique` | Galerie des peintures |
| `/about` | À propos |
| `/contact` | Formulaire de contact |
| `/register` | Inscription |
| `/login` | Connexion |
| `/panier` | Panier |
| `/checkout` | Paiement |

### Routes Administrateur

| Route | Description |
|-------|-------------|
| `/admin` | Tableau de bord |
| `/admin/paintings` | Gestion des peintures |
| `/admin/orders` | Gestion des commandes |
| `/admin/users` | Gestion des utilisateurs |
| `/admin/exhibitions` | Gestion des expositions |
| `/admin/settings` | Paramètres du site |

### Routes API

| Route | Description | Authentification |
|-------|-------------|------------------|
| `GET /api/export/full` | Export complet | API Key |
| `GET /api/export/orders` | Export des commandes | API Key |
| `GET /api/export/users` | Export des utilisateurs | API Key |
| `GET /api/export/paintings` | Export des peintures | API Key |
| `GET /api/export/settings` | Export des paramètres | API Key |
| `PUT /api/export/settings/<key>` | Mise à jour des paramètres | API Key |

---

## 🔐 Sécurité

### Authentification

- **Routes admin** : Protégées par `@require_admin` (session utilisateur)
- **Routes API** : Protégées par `@require_api_key` (header X-API-Key)

### Bonnes Pratiques

- ✅ Clé API forte et aléatoire
- ✅ HTTPS obligatoire en production
- ✅ Rotation régulière des clés
- ✅ Logging de tous les accès
- ✅ Rate limiting recommandé

---

## 📊 Base de Données

### Tables Principales

| Table | Description |
|-------|-------------|
| `paintings` | Peintures en vente |
| `orders` | Commandes clients |
| `order_items` | Articles des commandes |
| `users` | Utilisateurs/clients |
| `carts` | Paniers |
| `exhibitions` | Expositions |
| `custom_requests` | Demandes personnalisées |
| `settings` | Paramètres du site |
| `notifications` | Notifications |

### Initialisation

Les tables sont créées automatiquement au premier démarrage via `init_database()`.

---

## 🚀 Déploiement sur Scalingo

### Étapes

1. **Créer l'application**
   ```bash
   scalingo create template-artworksdigital
   ```

2. **Configurer les variables**
   ```bash
   scalingo env-set DATABASE_URL=...
   scalingo env-set TEMPLATE_MASTER_API_KEY=...
   ```

3. **Déployer**
   ```bash
   git push scalingo main
   ```

4. **Vérifier**
   ```bash
   scalingo logs
   ```

Voir [SUPABASE_SETUP.md](./SUPABASE_SETUP.md) pour les détails.

---

## 📈 Performance

### Optimisations Appliquées

- ✅ Détection des requêtes lentes (> 1s)
- ✅ Gestion des erreurs et rollback automatique
- ✅ Compression gzip recommandée
- ✅ Cache HTTP pour les images statiques
- ✅ Connexion pooling PostgreSQL

### Monitoring

```bash
# Vérifier les logs
scalingo logs --app template-artworksdigital

# Vérifier les variables
scalingo env --app template-artworksdigital
```

---

## 🔗 Intégration Dashboard

Le template communique avec le dashboard central via l'API :

```python
# Configuration
DASHBOARD_URL = "https://admin.artworksdigital.fr"
TEMPLATE_MASTER_API_KEY = "your-master-key"

# Endpoints disponibles
GET /api/export/full
GET /api/export/orders
GET /api/export/users
PUT /api/export/settings/<key>
```

Voir [API_INTEGRATION.md](./API_INTEGRATION.md) pour les détails.

---

## 🐛 Troubleshooting

### Erreur : "DATABASE_URL non configuré"

```bash
scalingo env-set DATABASE_URL=postgresql://...
scalingo restart
```

### Erreur : "API key invalide"

Vérifier la clé API :
```bash
scalingo env | grep TEMPLATE_MASTER_API_KEY
```

### Requêtes lentes

Vérifier les logs :
```bash
scalingo logs | grep "Slow query"
```

### Connexion Supabase refusée

1. Vérifier DATABASE_URL
2. Vérifier les pare-feu Supabase
3. Vérifier les logs Scalingo

---

## 📞 Support

### Ressources

- **Supabase** : https://supabase.com/docs
- **Scalingo** : https://doc.scalingo.com
- **Flask** : https://flask.palletsprojects.com
- **PostgreSQL** : https://www.postgresql.org/docs

### Contacter

- Dashboard : admin@artworksdigital.fr
- Support Scalingo : support@scalingo.com
- Support Supabase : support@supabase.com

---

## 📝 Changelog

### v1.0 (2025-12-07)

- ✅ Correction compatibilité PostgreSQL/RealDictCursor
- ✅ Correction gestion DATABASE_URL
- ✅ Ajout fonctions helpers pour accès aux données
- ✅ Nettoyage du projet (92% de réduction)
- ✅ Documentation complète
- ✅ Guides de configuration Supabase et Scalingo
- ✅ Guide d'intégration API

---

## 📄 Licence

Propriétaire - Artworksdigital

---

## 👥 Auteurs

- **Artworksdigital Team**
- **Dernière mise à jour** : 2025-12-07

---

**Pour commencer :** Voir [SUPABASE_SETUP.md](./SUPABASE_SETUP.md)
