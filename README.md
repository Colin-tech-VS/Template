# 🎨 Template - Application E-commerce pour Artistes

Application web complète pour la vente d'œuvres d'art en ligne, avec gestion des commandes, des expositions et des demandes sur mesure.

## 🆕 Migration Supabase/PostgreSQL

**Cette application utilise maintenant Supabase/PostgreSQL exclusivement.**

> ⚠️ SQLite n'est plus supporté. Voir [MIGRATION_COMPLETE.md](./MIGRATION_COMPLETE.md) pour les détails.

---

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.8+
- Compte Supabase (gratuit sur [supabase.com](https://supabase.com))

### Installation

```bash
# 1. Cloner le repository
git clone https://github.com/Colin-tech-VS/Template.git
cd Template

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer Supabase
cp .env.example .env
# Éditez .env et ajoutez votre SUPABASE_DB_URL
```

### Configuration Supabase

1. Créez un projet sur [app.supabase.com](https://app.supabase.com)
2. Allez dans `Settings > Database`
3. Copiez la **Connection string (URI)**
4. Ajoutez-la dans `.env`:

```bash
SUPABASE_DB_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
```

### Lancement

```bash
# Migrer vos données (si vous avez une base SQLite existante)
python migrate_sqlite_to_supabase.py

# Valider la migration
python test_supabase_migration.py

# Lancer l'application
python app.py
```

L'application sera accessible sur `http://localhost:5000`

---

## ✨ Fonctionnalités

### 🛒 E-commerce
- Boutique en ligne avec galerie d'œuvres
- Panier et gestion des commandes
- Paiement sécurisé avec Stripe
- Suivi des commandes

### 👤 Gestion des Utilisateurs
- Inscription et authentification
- Profils utilisateurs
- Rôles (utilisateur, admin, partenaire)
- Notifications

### 🎨 Gestion des Œuvres
- Upload et gestion des images
- Catégories et techniques
- Description détaillée (dimensions, année, etc.)
- Gestion du stock et des statuts

### 📅 Expositions
- Calendrier des expositions
- Détails des événements
- Intégration Google Places
- Galerie photos

### ✏️ Créations sur Mesure
- Formulaire de demande
- Upload d'images de référence
- Suivi des projets
- Communication client-artiste

### 🔧 Administration
- Dashboard complet
- Gestion des commandes
- Statistiques et exports
- Paramètres personnalisables

### 🌐 SaaS Multi-sites
- Support multi-tenant
- API d'export
- Intégration dashboard central
- Workflow de déploiement

---

## 🗄️ Architecture

### Base de Données (Supabase/PostgreSQL)

Tables principales:
- `users` - Utilisateurs et authentification
- `paintings` - Œuvres d'art
- `orders` & `order_items` - Commandes
- `exhibitions` - Expositions
- `custom_requests` - Demandes sur mesure
- `settings` - Paramètres de l'application
- `saas_sites` - Gestion multi-sites

### Stack Technique

**Backend:**
- Flask (Python)
- PostgreSQL via psycopg2
- Supabase

**Frontend:**
- HTML5/CSS3
- JavaScript vanilla
- Templates Jinja2

**Services:**
- Stripe (paiements)
- SMTP (emails)
- Google Places (localisation)

---

## 📚 Documentation

### Guides de Migration

- **[MIGRATION_COMPLETE.md](./MIGRATION_COMPLETE.md)** - Vue d'ensemble de la migration ✅
- **[SUPABASE_MIGRATION_GUIDE.md](./SUPABASE_MIGRATION_GUIDE.md)** - Guide détaillé pas à pas
- **[MIGRATION_SUMMARY.md](./MIGRATION_SUMMARY.md)** - Résumé technique

### Scripts Utilitaires

- `migrate_sqlite_to_supabase.py` - Migration automatique des données
- `test_supabase_migration.py` - Tests de validation
- `check_db_schema.py` - Vérification du schéma
- `reset_db.py` - Réinitialisation de la base (⚠️ destructif)
- `verify_db.py` - Vérification des paramètres

### API Documentation

Voir `TEMPLATE_API_SETUP.md` pour la documentation complète de l'API.

Endpoints principaux:
- `/api/export/*` - Exports de données
- `/api/stripe-pk` - Clé publique Stripe
- `/api/template/config` - Configuration du site
- `/webhook/stripe` - Webhooks Stripe

---

## 🔐 Sécurité

### Variables d'Environnement

Variables obligatoires:
```bash
SUPABASE_DB_URL=postgresql://...       # Connexion Supabase
TEMPLATE_MASTER_API_KEY=...            # Clé API maître
```

Variables optionnelles:
```bash
STRIPE_SECRET_KEY=sk_test_...          # Stripe
STRIPE_PUBLISHABLE_KEY=pk_test_...     # Stripe
SMTP_PASSWORD=...                       # Email
```

### Bonnes Pratiques

- ✅ Ne jamais committer `.env`
- ✅ Utiliser des clés différentes dev/prod
- ✅ Connexions SSL uniquement (Supabase)
- ✅ Secrets côté serveur
- ✅ Validation des entrées

### CodeQL

```bash
✅ 0 vulnérabilité détectée
```

---

## 🧪 Tests

### Tests de Migration

```bash
python test_supabase_migration.py
```

Tests disponibles:
1. Connexion Supabase
2. Vérification des tables
3. Opérations CRUD
4. Import de l'application
5. Validation du schéma

### Tests des Endpoints

```bash
python test_endpoints.py
python test_api.py
python test_stripe_api.py
```

---

## 🚀 Déploiement

### Render

```yaml
# render.yaml (exemple)
services:
  - type: web
    name: template-app
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: SUPABASE_DB_URL
        sync: false
      - key: TEMPLATE_MASTER_API_KEY
        generateValue: true
```

### Scalingo

```bash
# Ajouter les variables
scalingo env-set SUPABASE_DB_URL="postgresql://..."
scalingo env-set TEMPLATE_MASTER_API_KEY="votre-cle"

# Déployer
git push scalingo main
```

### Variables Requises

| Variable | Description | Obligatoire |
|----------|-------------|-------------|
| `SUPABASE_DB_URL` | URL de connexion Supabase | ✅ Oui |
| `TEMPLATE_MASTER_API_KEY` | Clé API maître | ✅ Oui |
| `STRIPE_SECRET_KEY` | Clé secrète Stripe | ⚠️ Si paiements |
| `SMTP_PASSWORD` | Mot de passe email | ⚠️ Si emails |

---

## 📊 Performances

### Supabase vs SQLite

| Métrique | SQLite | Supabase |
|----------|--------|----------|
| Connexions simultanées | 1 | Illimitées |
| Performances lecture | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Performances écriture | ⭐⭐ | ⭐⭐⭐⭐ |
| Scalabilité | Limitée | Excellente |
| Disponibilité | ~95% | 99.9% SLA |

---

## 🤝 Contribution

### Structure du Projet

```
Template/
├── app.py                  # Application principale
├── database.py             # Module Supabase
├── requirements.txt        # Dépendances
├── .env.example           # Configuration exemple
├── static/                # Assets statiques
├── templates/             # Templates HTML
├── migrate_*.py           # Scripts de migration
├── test_*.py              # Tests
└── *.md                   # Documentation
```

### Workflow de Développement

1. Fork le repository
2. Créer une branche (`git checkout -b feature/ma-fonctionnalite`)
3. Commiter les changements (`git commit -m 'Ajout fonctionnalité'`)
4. Pousser la branche (`git push origin feature/ma-fonctionnalite`)
5. Ouvrir une Pull Request

---

## 📞 Support

### Resources

- 📖 **Documentation**: Voir les fichiers `.md` du projet
- 🐛 **Issues**: [GitHub Issues](https://github.com/Colin-tech-VS/Template/issues)
- 💬 **Supabase**: [Discord Supabase](https://discord.supabase.com)
- 📧 **Contact**: Ouvrir une issue GitHub

### FAQ

**Q: Puis-je utiliser SQLite?**  
R: Non, SQLite n'est plus supporté. Utilisez Supabase (gratuit jusqu'à 500MB).

**Q: Comment migrer mes données?**  
R: Utilisez `migrate_sqlite_to_supabase.py` (voir documentation).

**Q: Coût de Supabase?**  
R: Gratuit jusqu'à 500MB DB + 2GB bande passante. Pro à partir de $25/mois.

---

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

## 🙏 Remerciements

- [Supabase](https://supabase.com) - Base de données
- [Stripe](https://stripe.com) - Paiements
- [Flask](https://flask.palletsprojects.com/) - Framework web
- [PostgreSQL](https://www.postgresql.org/) - Base de données

---

## 📈 Roadmap

### Version 1.x (Actuelle)
- ✅ Migration Supabase
- ✅ API complète
- ✅ SaaS multi-sites

### Version 2.0 (Prochaine)
- [ ] Supabase Auth
- [ ] Supabase Storage
- [ ] WebSockets temps réel
- [ ] PWA/Mobile

### Version 3.0 (Future)
- [ ] Multi-langue
- [ ] Marketplace
- [ ] Analytics avancés

---

**Créé avec ❤️ pour les artistes**
