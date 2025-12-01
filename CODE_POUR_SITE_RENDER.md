# 🚀 Déploiement du Template sur Render

## 📝 Ce qui est déjà configuré

Le template possède **déjà** le système d'auto-registration intégré ! 🎉

### ✅ Fonctionnalités automatiques

- **Génération d'API key** : Au premier démarrage, une clé unique est créée automatiquement
- **Enregistrement au dashboard** : Le site s'enregistre automatiquement sur `https://mydashboard-v39e.onrender.com`
- **Données envoyées** : Nom du site, URL, API key
- **Gestion des erreurs** : Continue de fonctionner même si le dashboard est indisponible

---

## 🎯 Déploiement sur Render

### 1️⃣ Créer un nouveau service Web

1. Va sur [Render Dashboard](https://dashboard.render.com/)
2. Clique sur **"New +"** → **"Web Service"**
3. Connecte ton repo GitHub `Colin-tech-VS/Template`
4. Configure :
   - **Name** : `site-artiste-nom` (exemple : `site-galerie-martin`)
   - **Branch** : `main`
   - **Runtime** : `Python 3`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn app:app` (ou `python app.py` en dev)

### 2️⃣ Variables d'environnement

Ajoute ces variables dans les settings Render :

```bash
# URL du site (optionnel, auto-détecté par Render)
SITE_URL=https://site-artiste-nom.onrender.com

# Activer l'auto-registration (optionnel, désactivé par défaut)
# ENABLE_AUTO_REGISTRATION=true

# Base de données (si PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Autres variables du template
STRIPE_SECRET_KEY=sk_test_...
SMTP_USER=email@gmail.com
SMTP_PASSWORD=mot_de_passe_app
```

### 3️⃣ Déployer

1. Clique sur **"Create Web Service"**
2. Render va :
   - Cloner le repo
   - Installer les dépendances
   - Lancer l'application
   - **Générer automatiquement l'API key**
   - **S'enregistrer sur ton dashboard**

---

## 📡 Ce qui se passe au premier démarrage

```python
# Au lancement de app.py
1. Migration de la base de données ✅
2. Vérification de l'API key...
   → Aucune clé trouvée
   → Génération automatique : "a1b2c3d4e5f6..."
   → Sauvegarde dans settings.export_api_key ✅
3. Vérification du setting enable_auto_registration
   → Si activé : Enregistrement sur le dashboard
   → Si désactivé : API key locale uniquement
4. Tentative d'enregistrement...
   POST https://mydashboard-v39e.onrender.com/api/sites/register
   {
     "site_name": "Galerie Martin",
     "site_url": "https://site-galerie-martin.onrender.com",
     "api_key": "a1b2c3d4e5f6...",
     "auto_registered": true
   }
5. Résultat :
   ✅ Si 200 → "Site enregistré sur le dashboard central"
   ⚠️ Si 404 → "L'API key est générée localement et reste fonctionnelle"
```

---

## 🔧 Activer l'auto-registration

Par défaut, l'auto-registration est **désactivée** pour éviter les erreurs 404.

### Option 1 : Via la base de données

```sql
INSERT INTO settings (key, value) 
VALUES ('enable_auto_registration', 'true')
ON CONFLICT (key) DO UPDATE SET value = 'true';
```

### Option 2 : Via l'API du site

```bash
# Depuis un terminal avec accès au site
curl -X POST https://site-artiste-nom.onrender.com/api/sync-dashboard
```

### Option 3 : Variable d'environnement Render

Ajoute dans les Environment Variables :

```bash
ENABLE_AUTO_REGISTRATION=true
```

Puis redéploie le service.

---

## 📊 Vérifier l'enregistrement

### Logs Render

Dans les logs du service, tu devrais voir :

```
✅ Clé API générée automatiquement: a1b2c3d4e5...
✅ Site enregistré sur le dashboard central: Galerie Martin
```

Ou si l'auto-registration est désactivée :

```
✅ Clé API générée automatiquement: a1b2c3d4e5...
ℹ️ Auto-registration désactivé. Génération de l'API key uniquement.
```

### Dashboard Central

Va sur `https://mydashboard-v39e.onrender.com/admin/sites` pour voir :

```
🌐 Sites Déployés
───────────────────────────────────
🎨 Galerie Martin
🔗 https://site-galerie-martin.onrender.com
🔑 API: a1b2c3d4e5... [Copier]
📅 Enregistré : 01/12/2025 14:30
🟢 Actif
```

---

## 🔄 Re-synchronisation manuelle

Si besoin de forcer une nouvelle synchronisation :

```bash
curl -X POST https://site-artiste-nom.onrender.com/api/sync-dashboard
```

---

## 🎨 Workflow complet : Déployer un site pour un artiste

### 1. Sur ton dashboard central

1. Un artiste fait une demande via le formulaire
2. Tu l'approuves dans "Gestion Artistes"

### 2. Cloner et déployer

```bash
# Clone le template
git clone https://github.com/Colin-tech-VS/Template.git site-artiste-nom
cd site-artiste-nom

# Crée un nouveau repo GitHub
gh repo create site-artiste-nom --private --source=. --push

# Ou via l'interface GitHub :
# - Crée un nouveau repo
# - Push le code
```

### 3. Déployer sur Render

1. Va sur Render → New Web Service
2. Connecte le nouveau repo
3. Configure les variables d'environnement
4. Déploie

### 4. Automatique ! 🎉

Le site :
- Génère son API key unique
- S'enregistre automatiquement sur ton dashboard
- Apparaît dans "Sites Déployés"

### 5. Associer à l'artiste (sur ton dashboard)

```python
# Dans ton dashboard, endpoint pour lier site et artiste
@app.route('/api/sites/<int:site_id>/link-artist/<int:artist_id>', methods=['POST'])
def link_site_to_artist(site_id, artist_id):
    site = Site.query.get_or_404(site_id)
    site.artist_id = artist_id
    db.session.commit()
    return jsonify({'success': True})
```

---

## 🔐 Sécurité

### API Key

- ✅ Générée avec `secrets.token_urlsafe(32)` (256 bits)
- ✅ Unique pour chaque site
- ✅ Invisible dans le dashboard admin artiste
- ✅ Stockée de manière sécurisée dans la base de données
- ✅ Utilisable immédiatement pour les endpoints API

### Endpoint d'enregistrement

Le dashboard central doit vérifier :
- Le domaine d'origine (`.onrender.com` autorisé)
- Limiter le taux d'enregistrement (rate limiting)
- Logger tous les enregistrements

---

## 🐛 Dépannage

### "⚠️ Erreur d'enregistrement: 404"

→ L'endpoint `/api/sites/register` n'existe pas encore sur ton dashboard
→ Solution : Ajoute le code dans `DASHBOARD_CENTRAL_CODE.md`
→ Le site continue de fonctionner normalement

### "⚠️ Impossible de contacter le dashboard central: Connection timeout"

→ Le dashboard est inaccessible
→ Vérifie que `https://mydashboard-v39e.onrender.com` est en ligne
→ Le site continue avec l'API key locale

### "ℹ️ Auto-registration désactivé"

→ C'est normal ! Active-le avec le setting `enable_auto_registration=true`

### L'API key n'est pas générée

→ Vérifie la migration de la base de données
→ Vérifie que la table `settings` existe
→ Check les logs Render pour les erreurs

---

## 📚 Documentation supplémentaire

- **AUTO_REGISTRATION_SYSTEM.md** : Documentation complète du système
- **DASHBOARD_CENTRAL_CODE.md** : Code à ajouter sur ton dashboard
- **API_EXPORT_DOCUMENTATION.md** : Documentation des endpoints API

---

## ✅ Checklist de déploiement

- [ ] Repo GitHub créé pour le site artiste
- [ ] Service Render configuré et déployé
- [ ] Variables d'environnement ajoutées
- [ ] Premier démarrage réussi (check logs)
- [ ] API key générée automatiquement
- [ ] Site visible sur le dashboard central (si activé)
- [ ] Tests des endpoints API fonctionnels
- [ ] Site accessible publiquement

---

## 🎯 Résultat final

```
Artiste demande → Tu approuves → Déploiement Render
                                        ↓
                                  Premier démarrage
                                        ↓
                              Génération API key auto
                                        ↓
                            Enregistrement sur dashboard
                                        ↓
                              Site opérationnel ! 🎉
```

                              Site opérationnel ! 🎉
```

---

## 💡 Note importante

**Le code est déjà intégré dans le template !** Tu n'as plus rien à ajouter manuellement.

Il suffit de :
1. Déployer le template sur Render
2. (Optionnel) Activer `enable_auto_registration=true`
3. Le reste est automatique ! 🚀
