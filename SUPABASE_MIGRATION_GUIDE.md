# 🚀 Guide de Migration SQLite → Supabase/PostgreSQL

Ce guide explique comment migrer votre application depuis SQLite vers Supabase/PostgreSQL.

## 📋 Table des Matières

1. [Prérequis](#prérequis)
2. [Configuration Supabase](#configuration-supabase)
3. [Migration des Données](#migration-des-données)
4. [Validation](#validation)
5. [Déploiement](#déploiement)
6. [Rollback](#rollback)
7. [FAQ](#faq)

---

## ✅ Prérequis

- Compte Supabase (gratuit sur [supabase.com](https://supabase.com))
- Python 3.8+
- Accès à vos bases SQLite locales (`paintings.db`, `app.db`)

## 🔧 Configuration Supabase

### 1. Créer un projet Supabase

1. Allez sur [app.supabase.com](https://app.supabase.com)
2. Créez un nouveau projet
3. Notez le mot de passe de la base de données (vous en aurez besoin)

### 2. Récupérer l'URL de connexion

1. Dans votre projet Supabase, allez dans `Settings > Database`
2. Copiez la **Connection string** (URI)
3. Format: `postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres`

### 3. Configurer les variables d'environnement

Créez un fichier `.env` à la racine du projet:

```bash
# .env
SUPABASE_DB_URL=postgresql://postgres:votre-mot-de-passe@db.xxxxx.supabase.co:5432/postgres

# Optionnel: clés API
TEMPLATE_MASTER_API_KEY=votre-cle-secrete
```

> ⚠️ **Important**: Ne commitez JAMAIS le fichier `.env` sur Git!

---

## 🔄 Migration des Données

### Option 1: Script de Migration Automatique (Recommandé)

Le script `migrate_sqlite_to_supabase.py` migre automatiquement toutes les données:

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Définir l'URL Supabase
export SUPABASE_DB_URL="postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres"

# 3. Lancer la migration
python migrate_sqlite_to_supabase.py
```

Le script va:
- ✅ Créer toutes les tables dans Supabase
- ✅ Migrer toutes les données depuis SQLite
- ✅ Gérer les conflits et les doublons
- ✅ Réinitialiser les séquences ID

### Option 2: Migration Manuelle

Si vous préférez migrer manuellement:

```bash
# 1. Exporter les données SQLite en SQL
sqlite3 paintings.db .dump > backup_sqlite.sql

# 2. Adapter le SQL pour PostgreSQL
# (Remplacer AUTOINCREMENT par SERIAL, etc.)

# 3. Importer dans Supabase
psql $SUPABASE_DB_URL < backup_adapted.sql
```

---

## ✅ Validation

### 1. Vérifier la Connexion

```bash
# Tester la connexion Supabase
python -c "from database import get_db; conn = get_db(); print('✅ Connexion OK')"
```

### 2. Vérifier les Tables

Dans l'interface Supabase (Table Editor):
- `users` → Vérifier qu'il y a des utilisateurs
- `paintings` → Vérifier qu'il y a des œuvres
- `orders` → Vérifier les commandes
- `settings` → Vérifier les paramètres

### 3. Tester l'Application

```bash
# Lancer l'application en local
python app.py
```

Testez les fonctionnalités critiques:
- ✅ Connexion/Inscription
- ✅ Affichage des œuvres
- ✅ Panier et commande
- ✅ Administration

### 4. Tester les Endpoints API

```bash
# Test avec curl
curl -H "X-API-Key: votre-cle" http://localhost:5000/api/export/settings
```

---

## 🚀 Déploiement

### Sur Render

1. Créez un service Web sur [render.com](https://render.com)
2. Connectez votre repository GitHub
3. Définissez les variables d'environnement:
   ```
   SUPABASE_DB_URL=postgresql://postgres:...@db.xxxxx.supabase.co:5432/postgres
   TEMPLATE_MASTER_API_KEY=votre-cle-secrete
   ```
4. Déployez!

### Sur Scalingo

1. Créez une application sur [scalingo.com](https://scalingo.com)
2. Définissez les variables d'environnement:
   ```bash
   scalingo env-set SUPABASE_DB_URL="postgresql://..."
   scalingo env-set TEMPLATE_MASTER_API_KEY="votre-cle"
   ```
3. Déployez avec Git:
   ```bash
   git push scalingo main
   ```

---

## ⏪ Rollback (Plan de Secours)

En cas de problème, vous pouvez revenir à SQLite:

### 1. Désactiver Supabase Temporairement

```bash
# Supprimer la variable d'environnement
unset SUPABASE_DB_URL
```

> ⚠️ **Note**: Avec cette migration, SQLite n'est plus supporté. 
> Il faudrait restaurer l'ancien fichier `database.py` pour revenir à SQLite.

### 2. Restaurer une Sauvegarde

Si vous avez une sauvegarde Supabase:

```bash
# Via l'interface Supabase
# Settings > Database > Backups > Restore
```

---

## ❓ FAQ

### Q: Puis-je utiliser SQLite en développement et Supabase en production?

**R:** Non, après cette migration, l'application utilise exclusivement Supabase/PostgreSQL. 
Vous pouvez créer un projet Supabase gratuit pour le développement.

### Q: Comment sauvegarder ma base Supabase?

**R:** Supabase fait des sauvegardes automatiques quotidiennes. 
Vous pouvez aussi exporter manuellement via `pg_dump`:

```bash
pg_dump $SUPABASE_DB_URL > backup.sql
```

### Q: Les performances sont-elles meilleures avec Supabase?

**R:** Oui! PostgreSQL/Supabase est plus performant que SQLite pour:
- Accès concurrents multiples
- Volumes de données importants
- Transactions complexes
- Scalabilité

### Q: Combien coûte Supabase?

**R:** 
- **Gratuit** jusqu'à 500 MB de base de données et 2 GB de bande passante
- **Pro** à partir de $25/mois pour des besoins plus importants
- Voir [supabase.com/pricing](https://supabase.com/pricing)

### Q: Que faire si la migration échoue?

**R:**
1. Vérifiez vos identifiants Supabase
2. Vérifiez que votre projet Supabase est actif
3. Consultez les logs d'erreur du script
4. Contactez le support si nécessaire

### Q: Comment gérer plusieurs environnements (dev/staging/prod)?

**R:** Créez un projet Supabase par environnement:

```bash
# .env.development
SUPABASE_DB_URL=postgresql://...@db.dev-xxxxx.supabase.co:5432/postgres

# .env.production
SUPABASE_DB_URL=postgresql://...@db.prod-xxxxx.supabase.co:5432/postgres
```

---

## 📞 Support

- Documentation Supabase: [supabase.com/docs](https://supabase.com/docs)
- Documentation PostgreSQL: [postgresql.org/docs](https://www.postgresql.org/docs/)
- Issues GitHub: Ouvrez une issue sur le repository

---

## ✨ Avantages de Supabase

✅ **Haute disponibilité** - Infrastructure managée  
✅ **Sauvegardes automatiques** - Pas de perte de données  
✅ **Scalabilité** - Gérez des milliers d'utilisateurs  
✅ **Sécurité** - Connexions SSL, authentification avancée  
✅ **API temps réel** - WebSockets intégrés  
✅ **Interface graphique** - Visualisez et modifiez vos données  
✅ **Gratuit pour démarrer** - Idéal pour les MVPs  

---

**🎉 Félicitations! Votre application utilise maintenant Supabase/PostgreSQL.**
