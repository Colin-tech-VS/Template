# 🚀 Déploiement du Template sur Render

## ✅ Le code est déjà intégré !

**Bonne nouvelle** : Le système d'auto-registration est **déjà dans le template** ! Tu n'as **rien à ajouter** au code.

---

## 📋 Ce qui est automatique

Au premier démarrage du site, le template :

1. ✅ **Vérifie si une API key existe**
   - Si non → Génère une clé unique avec `secrets.token_urlsafe(32)`
   - Si oui → Réutilise la clé existante (ne change JAMAIS)

2. ✅ **Vérifie le setting `enable_auto_registration`**
   - Si `false` ou inexistant → Génère juste l'API key locale
   - Si `true` → Enregistre le site sur ton dashboard

3. ✅ **Envoie les données au dashboard** (si activé)
   ```
   POST https://mydashboard-v39e.onrender.com/api/sites/register
   {
     "site_name": "Galerie Artiste",
     "site_url": "https://site-artiste.onrender.com",
     "api_key": "clé_générée_automatiquement",
     "auto_registered": true
   }
   ```

4. ✅ **Gère les réponses**
   - 200 → Site enregistré, stocke le `dashboard_id`
   - 404 → Dashboard pas prêt, continue avec l'API locale
   - Timeout → Inaccessible, continue normalement

---

## 🎯 Déployer un nouveau site pour un artiste

### Étape 1 : Cloner le template

```bash
# Clone le repo template
git clone https://github.com/Colin-tech-VS/Template.git galerie-artiste-nom

cd galerie-artiste-nom

# Crée un nouveau repo GitHub
gh repo create galerie-artiste-nom --private --push --source=.
```

### Étape 2 : Déployer sur Render

1. Va sur [Render Dashboard](https://dashboard.render.com/)
2. **New +** → **Web Service**
3. Connecte le nouveau repo
4. Configure :
   - **Name** : `galerie-artiste-nom`
   - **Branch** : `main`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn app:app`

### Étape 3 : Variables d'environnement (Important !)

Ajoute ces variables dans Render :

```bash
# Base de données PostgreSQL (fournie par Render)
DATABASE_URL=postgresql://...

# URL du site (auto-détectée si omise)
SITE_URL=https://galerie-artiste-nom.onrender.com

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# Email SMTP
SMTP_USER=ton.email@gmail.com
SMTP_PASSWORD=mot_de_passe_app

# Google Places (optionnel)
GOOGLE_PLACES_API_KEY=AIza...

# ⚠️ ACTIVER L'AUTO-REGISTRATION (optionnel)
# ENABLE_AUTO_REGISTRATION=true
```

### Étape 4 : Déployer

Clique sur **"Create Web Service"**

Render va :
- Installer les dépendances
- Migrer la base de données
- **Générer l'API key automatiquement**
- Démarrer le serveur
- ✅ Site opérationnel !

---

## 🔧 Activer l'auto-registration

Par défaut, l'auto-registration est **désactivée** pour éviter les erreurs 404.

### Option 1 : Via variable d'environnement Render

Dans les settings Render, ajoute :

```bash
ENABLE_AUTO_REGISTRATION=true
```

Puis redéploie.

### Option 2 : Via la base de données

```sql
-- Se connecter à PostgreSQL Render
INSERT INTO settings (key, value) 
VALUES ('enable_auto_registration', 'true')
ON CONFLICT (key) DO UPDATE SET value = 'true';
```

### Option 3 : Via l'endpoint de sync

```bash
curl -X POST https://galerie-artiste-nom.onrender.com/api/sync-dashboard
```

---

## 📊 Vérifier l'enregistrement

### Dans les logs Render

Cherche ces lignes :

```
✅ Clé API générée automatiquement: a1b2c3d4e5...
```

Si auto-registration activé :
```
📤 Enregistrement du site sur le dashboard central...
   Nom: Galerie Artiste
   URL: https://galerie-artiste-nom.onrender.com
✅ Site enregistré sur le dashboard central!
   Site ID: 42
```

Si désactivé :
```
ℹ️ Auto-registration désactivé. Génération de l'API key uniquement.
```

### Sur ton dashboard

Va sur `https://mydashboard-v39e.onrender.com/admin/sites`

Tu devrais voir :

```
🌐 Sites Déployés
──────────────────────────────
🎨 Galerie Artiste
🔗 https://galerie-artiste-nom.onrender.com
🔑 API: a1b2c3d4e5... [Copier]
📅 Enregistré : 01/12/2025 15:30
🟢 Actif
```

---

## 🔄 Re-synchronisation manuelle

Si le site n'apparaît pas dans le dashboard :

```bash
# Force une nouvelle synchronisation
curl -X POST https://galerie-artiste-nom.onrender.com/api/sync-dashboard
```

---

## 🎨 Workflow complet

```
1. Artiste fait une demande sur ton dashboard
        ↓
2. Tu approuves l'artiste
        ↓
3. Tu clones le template + crée un nouveau repo
        ↓
4. Tu déploies sur Render
        ↓
5. Au premier démarrage :
   - Génération API key automatique
   - Enregistrement sur ton dashboard (si activé)
        ↓
6. Le site apparaît dans "Sites Déployés"
        ↓
7. Tu lies le site à l'artiste sur ton dashboard
        ↓
8. ✅ L'artiste peut gérer son site !
```

---

## 🔐 Sécurité

### API Key

- ✅ Générée avec `secrets.token_urlsafe(32)` (256 bits)
- ✅ **Unique et permanente** par site
- ✅ Ne change JAMAIS au redémarrage
- ✅ Invisible dans le dashboard admin artiste
- ✅ Stockée dans `settings.export_api_key`

### Auto-registration

- ✅ Désactivé par défaut (évite erreurs 404)
- ✅ Activable via setting ou env variable
- ✅ Pas de doublon (vérification par URL)
- ✅ Update automatique si URL existe déjà

---

## 🐛 Dépannage

### "⚠️ Erreur d'enregistrement: 404"

**Cause** : L'endpoint `/api/sites/register` n'existe pas sur ton dashboard

**Solution** :
1. Ajoute le code dans `DASHBOARD_CENTRAL_CODE.md` sur ton dashboard
2. Ou désactive l'auto-registration pour l'instant
3. Le site continue de fonctionner avec l'API locale

### "ℹ️ Auto-registration désactivé"

**Cause** : Le setting `enable_auto_registration` n'est pas à `true`

**Solution** : Active-le via une des 3 options ci-dessus

### "⚠️ Impossible de déterminer l'URL du site"

**Cause** : Variables d'environnement manquantes

**Solution** : Ajoute `SITE_URL` dans les settings Render

### L'API key change à chaque redémarrage

**Impossible** : L'API key est générée UNE SEULE FOIS et stockée en base de données. Si elle change, c'est que la base de données est réinitialisée.

---

## ✅ Checklist de déploiement

- [ ] Repo GitHub créé pour le site artiste
- [ ] Service Render configuré
- [ ] Variables d'environnement ajoutées (DATABASE_URL, SMTP, etc.)
- [ ] Premier déploiement lancé
- [ ] Vérification des logs : "✅ Clé API générée"
- [ ] (Optionnel) Auto-registration activé
- [ ] (Optionnel) Site visible sur le dashboard central
- [ ] Tests des endpoints API fonctionnels
- [ ] Site accessible publiquement

---

## 📚 Documentation complémentaire

- **AUTO_REGISTRATION_SYSTEM.md** : Fonctionnement détaillé du système
- **DASHBOARD_CENTRAL_CODE.md** : Code à ajouter sur ton dashboard
- **API_EXPORT_DOCUMENTATION.md** : Documentation des endpoints API

---

## 💡 Points importants

1. **Le code est déjà dans le template** - Pas besoin d'ajouter quoi que ce soit
2. **L'API key est générée automatiquement** - UNE SEULE FOIS
3. **L'auto-registration est optionnelle** - Activable quand ton dashboard est prêt
4. **Pas de doublon** - Le système vérifie avant d'enregistrer
5. **Gestion des erreurs** - Le site fonctionne même si le dashboard est down

---

## 🚀 En résumé

```
Déployer sur Render → API générée auto → Site fonctionnel
                              ↓
                    (Optionnel) Enregistrement sur dashboard
                              ↓
                      Visible dans "Sites Déployés"
```

**C'est tout !** Le système gère tout automatiquement 🎉
