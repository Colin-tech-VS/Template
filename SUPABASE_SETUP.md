# Configuration Supabase et Scalingo

## 📋 Résumé

Ce guide explique comment configurer le projet pour utiliser **Supabase** (PostgreSQL hébergé) avec **Scalingo** (hébergeur).

---

## 1. Configuration Supabase

### Étape 1 : Créer un projet Supabase

1. Allez sur [supabase.com](https://supabase.com)
2. Cliquez sur **"New Project"**
3. Remplissez les informations :
   - **Project name** : `artworksdigital-template`
   - **Database password** : Générez un mot de passe fort
   - **Region** : Choisissez la région la plus proche (ex: `eu-west-1` pour Europe)
4. Cliquez sur **"Create new project"**

### Étape 2 : Récupérer la DATABASE_URL

1. Une fois le projet créé, allez dans **Settings > Database**
2. Cherchez la section **"Connection string"**
3. Sélectionnez le mode **"URI"**
4. Copiez la chaîne de connexion (elle ressemble à) :
   ```
   postgresql://postgres:YOUR_PASSWORD@db.supabase.co:5432/postgres
   ```

### Étape 3 : Initialiser les tables

Les tables seront créées automatiquement au premier démarrage de l'application.

---

## 2. Configuration Scalingo

### Étape 1 : Créer l'application Scalingo

```bash
# Installer Scalingo CLI
# https://doc.scalingo.com/platform/cli

# Créer l'application
scalingo create template-artworksdigital

# Ou si elle existe déjà
scalingo --app template-artworksdigital
```

### Étape 2 : Configurer les variables d'environnement

```bash
# Définir la DATABASE_URL
scalingo env-set DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@db.supabase.co:5432/postgres"

# Définir les clés API
scalingo env-set TEMPLATE_MASTER_API_KEY="your-master-key-here"
scalingo env-set STRIPE_SECRET_KEY="sk_test_..."
scalingo env-set STRIPE_PUBLISHABLE_KEY="pk_test_..."

# Définir la clé secrète Flask
scalingo env-set SECRET_KEY="your-secret-key-here"

# Définir l'URL du dashboard
scalingo env-set DASHBOARD_URL="https://admin.artworksdigital.fr"

# Vérifier les variables
scalingo env
```

### Étape 3 : Déployer l'application

```bash
# Ajouter le remote Scalingo
git remote add scalingo git@scalingo.com:template-artworksdigital.git

# Déployer
git push scalingo main

# Vérifier le déploiement
scalingo logs --app template-artworksdigital
```

---

## 3. Vérification de la Connexion

### Test 1 : Vérifier la variable DATABASE_URL

```bash
scalingo env | grep DATABASE_URL
```

Résultat attendu :
```
DATABASE_URL=postgresql://postgres:...@db.supabase.co:5432/postgres
```

### Test 2 : Vérifier les logs

```bash
scalingo logs --app template-artworksdigital
```

Cherchez les messages :
```
[DB] PostgreSQL/Supabase configuré: db.supabase.co:5432/postgres
[DB] ✓ Base de données centrale initialisée (PostgreSQL/Supabase)
```

### Test 3 : Tester l'API

```bash
# Récupérer la clé API
MASTER_KEY=$(scalingo env | grep TEMPLATE_MASTER_API_KEY | cut -d= -f2)

# Tester l'endpoint
curl -X GET https://template.artworksdigital.fr/api/export/full \
  -H "X-API-Key: $MASTER_KEY"
```

Résultat attendu : JSON avec les données du site

---

## 4. Troubleshooting

### Erreur : "DATABASE_URL non configuré"

**Cause** : La variable DATABASE_URL n'est pas définie

**Solution** :
```bash
scalingo env-set DATABASE_URL="postgresql://..."
scalingo restart
```

### Erreur : "connection refused"

**Cause** : Supabase n'est pas accessible

**Solution** :
1. Vérifiez que DATABASE_URL est correcte
2. Vérifiez que Supabase est en ligne
3. Vérifiez les pare-feu/IP whitelist dans Supabase

### Erreur : "SSL error"

**Cause** : SSL n'est pas configuré correctement

**Solution** :
Le code configure automatiquement `sslmode=require` pour Supabase. Pas d'action requise.

### Requêtes lentes

**Cause** : Connexion à la base de données lente

**Solution** :
1. Vérifiez les logs : `scalingo logs`
2. Optimisez les requêtes SQL
3. Ajoutez des index Supabase si nécessaire

---

## 5. Maintenance Supabase

### Sauvegardes

Supabase effectue des sauvegardes automatiques. Vous pouvez aussi :

1. Allez dans **Settings > Backups**
2. Cliquez sur **"Create backup"**
3. Téléchargez le backup si nécessaire

### Monitoring

1. Allez dans **Database > Logs**
2. Consultez les requêtes lentes
3. Optimisez si nécessaire

### Mise à jour

Supabase gère les mises à jour automatiquement. Pas d'action requise.

---

## 6. Liaison avec admin.artworksdigital.fr

### Configuration du Dashboard

Le dashboard central peut accéder aux données via l'API :

```python
# URL de l'API
https://template.artworksdigital.fr/api/export/full

# Headers requis
X-API-Key: your-master-key-here
```

### Endpoints disponibles

| Endpoint | Description |
|----------|-------------|
| `GET /api/export/full` | Export complet |
| `GET /api/export/orders` | Commandes |
| `GET /api/export/users` | Utilisateurs |
| `GET /api/export/paintings` | Peintures |
| `GET /api/export/exhibitions` | Expositions |
| `GET /api/export/settings` | Paramètres |
| `PUT /api/export/settings/<key>` | Mise à jour |

---

## 7. Checklist de Configuration

- [ ] Projet Supabase créé
- [ ] DATABASE_URL récupérée
- [ ] Application Scalingo créée
- [ ] DATABASE_URL configurée dans Scalingo
- [ ] TEMPLATE_MASTER_API_KEY configurée
- [ ] STRIPE_SECRET_KEY configurée
- [ ] SECRET_KEY configurée
- [ ] Application déployée
- [ ] Logs vérifiés (pas d'erreur)
- [ ] API testée avec curl
- [ ] Tables créées dans Supabase

---

## 📞 Support

### Supabase
- Documentation : https://supabase.com/docs
- Support : https://supabase.com/support

### Scalingo
- Documentation : https://doc.scalingo.com
- Support : https://scalingo.com/support

### PostgreSQL
- Documentation : https://www.postgresql.org/docs

---

**Dernière mise à jour :** 2025-12-07
**Version :** 1.0
