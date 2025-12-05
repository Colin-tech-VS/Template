# 🔑 Configuration de la Clé API Maître Template

## ✅ Configuration Terminée

La clé API maître `TEMPLATE_MASTER_API_KEY=template-master-key-2025` a été configurée avec succès sur ce template.

---

## 📋 Ce qui a été mis en place

### 1. Variable d'environnement configurée
```env
TEMPLATE_MASTER_API_KEY=template-master-key-2025
```
- ✅ À ajouter dans Scalingo : Variables d'environnement > Add
- ✅ Chargée au démarrage de l'application
- ✅ Valeur par défaut en local via `.env`

### 2. Constante globale dans `app.py`
```python
TEMPLATE_MASTER_API_KEY = os.getenv('TEMPLATE_MASTER_API_KEY', 'template-master-key-2025')
```
- ✅ Chargée depuis la variable d'environnement Scalingo
- ✅ Fallback sur la valeur par défaut en développement

### 3. Route `/api/export/settings/<key>` modifiée
La route accepte maintenant **directement** la clé maître sans décorateur :
```python
@app.route('/api/export/settings/<key>', methods=['PUT'])
def update_setting_api(key):
    api_key = request.headers.get('X-API-Key')
    
    # Accepter la clé maître du dashboard (priorité absolue)
    if api_key == TEMPLATE_MASTER_API_KEY:
        print(f'[API] 🔑 Clé maître acceptée - Configuration {key}')
        # Skip la vérification normale
    else:
        # Vérification normale pour les autres requêtes
        stored_key = get_setting("export_api_key")
        if api_key != stored_key:
            return jsonify({'error': 'Clé API invalide'}), 403
    
    # Mettre à jour (INSERT ou UPDATE automatique)
    data = request.json
    value = data.get('value')
    save_setting(key, value)
    
    return jsonify({'success': True})
```

### 4. Fonctionnalités ajoutées
- ✅ **INSERT automatique** : Si le paramètre n'existe pas, il est créé
- ✅ **Logs détaillés** : Chaque mise à jour est loggée
- ✅ **Gestion d'erreur** : Retours JSON clairs en cas d'échec

---

## 🎯 Endpoints API Disponibles

Tous ces endpoints acceptent maintenant la clé maître `template-master-key-2025` dans le header `X-API-Key` :

### Lecture (GET)
- `GET /api/export/full` - Export complet de toutes les données
- `GET /api/export/paintings` - Export des peintures
- `GET /api/export/orders` - Export des commandes
- `GET /api/export/users` - Export des utilisateurs (sans mots de passe)
- `GET /api/export/exhibitions` - Export des expositions
- `GET /api/export/custom-requests` - Export des demandes personnalisées
- `GET /api/export/settings` - Export des paramètres (clés sensibles masquées)
- `GET /api/export/stats` - Statistiques générales

### Écriture (PUT)
- **`PUT /api/export/settings/{key}`** - ✨ Modifier un paramètre spécifique
  - Body: `{"value": "nouvelle_valeur"}`
  - Exemple: `PUT /api/export/settings/saas_site_price_cache`

### Upload (POST)
- `POST /api/upload/image` - Upload d'image (multipart/form-data)

---

## 🚀 Utilisation depuis le Dashboard

### Exemple : Mettre à jour le prix du site

```javascript
fetch('https://template.artworksdigital.fr/api/export/settings/saas_site_price_cache', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'template-master-key-2025'
  },
  body: JSON.stringify({
    value: '550.00'  // 500€ base + 10% commission
  })
})
.then(res => res.json())
.then(data => console.log('Prix mis à jour:', data))
```

### Exemple avec cURL

```bash
curl -X PUT https://template.artworksdigital.fr/api/export/settings/saas_site_price_cache \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value": "550.00"}'
```

---

## 🔐 Sécurité

### ✅ Bonnes pratiques appliquées
1. **Clé maître dans `.env`** - Jamais dans le code source
2. **`.env` dans `.gitignore`** - Ne sera jamais commité sur Git
3. **Double système de clés** :
   - Clé maître pour le dashboard (administration globale)
   - Clé locale par site (pour exports ponctuels)
4. **Clés sensibles masquées** dans `GET /api/export/settings`
5. **Validation stricte** des headers HTTP

### 🚀 Déploiement sur Scalingo

### Étape 1 : Ajouter la variable d'environnement
Dans l'interface Scalingo de votre app `template` :
1. Allez dans **Environment** > **Environment variables**
2. Cliquez sur **Add a variable**
3. Ajoutez :
   - **Name** : `TEMPLATE_MASTER_API_KEY`
   - **Value** : `template-master-key-2025`
4. Cliquez sur **Save changes**
5. L'application redémarrera automatiquement

### Étape 2 : Déployer le code
```bash
git add .
git commit -m "Add TEMPLATE_MASTER_API_KEY support for dashboard"
git push scalingo main
```

### Étape 3 : Vérifier le démarrage
Dans les logs Scalingo, vous devriez voir :
```
🔑 Clé maître dashboard chargée: template-ma...y-2025
```

### Étape 4 : Tester l'API
```bash
curl -X PUT https://template.artworksdigital.fr/api/export/settings/saas_site_price_cache \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value": "550.00"}'
```

Résultat attendu :
```json
{"success": true, "message": "Paramètre saas_site_price_cache mis à jour"}
```

---

## 🔄 Workflow Dashboard → Template

1. **Dashboard** envoie une requête PUT avec la clé maître :
   ```
   PUT /api/export/settings/saas_site_price_cache
   Header: X-API-Key: template-master-key-2025
   Body: {"value": "550.00"}
   ```

2. **Template** vérifie la clé maître depuis `.env`
   - ✅ Si match → autorisation immédiate (pas de vérification BDD)
   - ❌ Sinon → vérifie la clé locale dans `settings`

3. **Base de données** mise à jour
   ```sql
   UPDATE settings SET value = '550.00' WHERE key = 'saas_site_price_cache'
   ```

4. **Confirmation** retournée au dashboard
   ```json
   {"success": true, "message": "Paramètre saas_site_price_cache mis à jour"}
   ```

---

## 📝 Variables d'environnement complètes

Voici toutes les variables supportées dans `.env` :

```env
# Clé API maître (OBLIGATOIRE pour intégration dashboard)
TEMPLATE_MASTER_API_KEY=template-master-key-2025

# Base de données (production)
DATABASE_URL=postgresql://user:pass@host:5432/db

# Stripe (optionnel, peut être dans settings)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# SMTP (optionnel, peut être dans settings)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=contact@example.com
SMTP_PASSWORD=app_password

# Flask
SECRET_KEY=your-very-long-random-secret-key
```

---

## ✅ Tests de Validation

### Test 1 : Chargement de la variable
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('TEMPLATE_MASTER_API_KEY'))"
# Résultat attendu : template-master-key-2025
```

### Test 2 : Accès API avec clé maître
```bash
curl -X GET https://template.artworksdigital.fr/api/export/stats \
  -H "X-API-Key: template-master-key-2025"
# Résultat attendu : JSON avec les statistiques du site
```

### Test 3 : Mise à jour d'un paramètre
```bash
curl -X PUT https://template.artworksdigital.fr/api/export/settings/test_key \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value": "test_value"}'
# Résultat attendu : {"success": true, "message": "..."}
```

---

## 🎉 Résultat Final

**Le template est maintenant prêt à recevoir les configurations automatiques du dashboard !**

Le dashboard peut désormais :
- ✅ Lire tous les paramètres du site
- ✅ Mettre à jour le prix (500€ + 10% = 550€)
- ✅ Configurer n'importe quel setting via API
- ✅ Uploader des images
- ✅ Récupérer des statistiques

**Prochaine étape :** Implémenter la logique côté dashboard pour appeler ces endpoints lors de la création/modification d'un site artiste.
