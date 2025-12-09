# 🔗 Guide d'Intégration Template — MyDashboard

## 📋 Vue d'ensemble

Ce guide explique comment intégrer un site **Template** avec le **Dashboard** (système de gestion centralisé). Le Dashboard permet de gérer plusieurs sites d'artistes basés sur ce template, de configurer automatiquement les prix, les clés Stripe, et de superviser les déploiements.

### Architecture

```
Dashboard (admin.artworksdigital.fr)
    ↓
    | Configuration automatique via API
    ↓
Template Sites (template.artworksdigital.fr, artiste1.artworksdigital.fr, etc.)
```

---

## ✅ Pré-requis

### Côté Template
- Flask application déployée (Scalingo, Heroku, ou autre)
- Base de données configurée (SQLite ou PostgreSQL)
- Accès HTTPS en production
- Variable d'environnement `TEMPLATE_MASTER_API_KEY` configurée

### Côté Dashboard
- Clé maître partagée (`TEMPLATE_MASTER_API_KEY`)
- Liste des sites à gérer (URLs)
- Configuration Stripe (publishable key et secret key)

---

## 🔑 1. Configuration de la Clé API Maître

### 1.1 Qu'est-ce que la clé maître ?

La clé maître (`TEMPLATE_MASTER_API_KEY`) est un secret partagé entre le Dashboard et tous les sites Template. Elle permet au Dashboard de :
- ✅ Configurer automatiquement les paramètres des sites
- ✅ Pousser les clés Stripe
- ✅ Mettre à jour les prix SAAS
- ✅ Gérer les paramètres sans connaître les clés locales de chaque site

**Valeur recommandée :** `template-master-key-2025`

### 1.2 Configuration sur le Template

#### Étape 1 : Ajouter la variable d'environnement

**Sur Scalingo :**
```
Dashboard > Environment > Environment variables > Add a variable
Name:  TEMPLATE_MASTER_API_KEY
Value: template-master-key-2025
```

**En local (.env) :**
```env
TEMPLATE_MASTER_API_KEY=template-master-key-2025
```

**IMPORTANT :** Ne jamais committer cette clé dans le code source. Assurez-vous que `.env` est dans `.gitignore`.

#### Étape 2 : Charger la clé dans l'application

Dans `app.py`, ajoutez en haut du fichier (après les imports) :

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Clé API maître pour authentification Dashboard
TEMPLATE_MASTER_API_KEY = os.getenv('TEMPLATE_MASTER_API_KEY', 'template-master-key-2025')
print(f"🔑 Clé maître dashboard chargée: {TEMPLATE_MASTER_API_KEY[:10]}...{TEMPLATE_MASTER_API_KEY[-5:]}")
```

---

## 🎯 2. Endpoints API Disponibles

### 2.1 Endpoints de Lecture (GET)

Ces endpoints permettent au Dashboard de récupérer les données du site :

| Endpoint | Description | Authentification |
|----------|-------------|------------------|
| `GET /api/export/full` | Export complet de toutes les données | Clé maître ou clé locale |
| `GET /api/export/paintings` | Export des peintures | Clé maître ou clé locale |
| `GET /api/export/orders` | Export des commandes | Clé maître ou clé locale |
| `GET /api/export/users` | Export des utilisateurs (sans mots de passe) | Clé maître ou clé locale |
| `GET /api/export/exhibitions` | Export des expositions | Clé maître ou clé locale |
| `GET /api/export/settings` | Export des paramètres (clés sensibles masquées) | Clé maître ou clé locale |
| `GET /api/export/stats` | Statistiques générales | Clé maître ou clé locale |
| `GET /api/stripe-pk` | Récupération de la Stripe Publishable Key | Public (pas d'authentification) |

**Exemple d'utilisation :**

```bash
curl -X GET https://template.artworksdigital.fr/api/export/stats \
  -H "X-API-Key: template-master-key-2025"
```

### 2.2 Endpoints d'Écriture (PUT)

Ces endpoints permettent au Dashboard de configurer le site :

| Endpoint | Description | Body |
|----------|-------------|------|
| `PUT /api/export/settings/<key>` | Modifier un paramètre spécifique | `{"value": "nouvelle_valeur"}` |
| `PUT /api/export/settings/stripe_publishable_key` | Configurer la clé Stripe publique | `{"value": "pk_test_..."}` |
| `PUT /api/export/settings/stripe_secret_key` | Configurer la clé Stripe secrète | `{"value": "sk_test_..."}` |
| `PUT /api/export/settings/saas_site_price_cache` | Configurer le prix SAAS | `{"value": "550.00"}` |

**Exemple : Configurer le prix du site**

```bash
curl -X PUT https://template.artworksdigital.fr/api/export/settings/saas_site_price_cache \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value": "550.00"}'
```

### 2.3 Endpoint d'Upload (POST)

| Endpoint | Description | Type |
|----------|-------------|------|
| `POST /api/upload/image` | Upload d'image | multipart/form-data |

---

## 🔐 3. Authentification des Endpoints

### 3.1 Logique d'authentification

Les endpoints `/api/export/settings/*` acceptent **deux types de clés** :

1. **Clé maître** (priorité absolue) : `TEMPLATE_MASTER_API_KEY`
   - Utilisée par le Dashboard
   - Accès complet à tous les paramètres
   - Pas de vérification en base de données

2. **Clé locale** : `export_api_key` (stockée dans la table `settings`)
   - Utilisée pour des exports ponctuels
   - Validation en base de données
   - Moins de privilèges

### 3.2 Implémentation

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
    
    return jsonify({'success': True, 'message': f'Paramètre {key} mis à jour'})
```

---

## 💳 4. Intégration Stripe

### 4.1 Vue d'ensemble

Le Template nécessite deux clés Stripe :
- **Publishable Key** (`pk_*`) : Utilisée côté client (JavaScript) pour initialiser Stripe.js
- **Secret Key** (`sk_*`) : Utilisée côté serveur pour créer des sessions de paiement

### 4.2 Configuration de la Publishable Key

#### Côté Template : Endpoint de lecture

```python
@app.route('/api/stripe-pk', methods=['GET'])
def api_stripe_pk():
    """Retourne la publishable key pour initialisation Stripe.js côté client"""
    # 1) Lecture locale (settings ou variable d'environnement)
    pk = get_setting('stripe_publishable_key') or os.getenv('STRIPE_PUBLISHABLE_KEY')
    if pk:
        return jsonify({"success": True, "publishable_key": pk})
    
    # 2) Fallback optionnel : interroger le dashboard (si configuré)
    dashboard_url = os.getenv('DASHBOARD_URL')
    site_name = os.getenv('SITE_NAME')
    if dashboard_url and site_name:
        try:
            resp = requests.get(
                f"{dashboard_url}/api/sites/{site_name}/stripe-key",
                timeout=5
            )
            if resp.ok:
                data = resp.json()
                if data.get('success') and data.get('publishable_key'):
                    return jsonify({
                        "success": True,
                        "publishable_key": data.get('publishable_key')
                    })
        except Exception as e:
            print(f"Erreur fallback dashboard: {e}")
    
    return jsonify({"success": False, "message": "no_publishable_key"}), 404
```

#### Côté Template : Endpoint d'écriture

```python
@app.route('/api/export/settings/stripe_publishable_key', methods=['PUT'])
def import_setting_stripe_pk():
    """Reçoit la publishable key poussée par le Dashboard"""
    api_key = request.headers.get('X-API-Key')
    
    # Vérification de la clé maître
    if api_key != TEMPLATE_MASTER_API_KEY:
        return jsonify({"success": False, "error": "unauthorized"}), 403
    
    body = request.get_json(silent=True) or {}
    value = body.get('value')
    if not value:
        return jsonify({"success": False, "error": "missing_value"}), 400
    
    try:
        save_setting('stripe_publishable_key', value)
        print(f"✅ Stripe PK configurée: {value[:10]}...")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
```

#### Côté Client : Initialisation Stripe.js

**1. Charger Stripe.js dans le HTML :**

```html
<script src="https://js.stripe.com/v3/"></script>
```

**2. Initialiser Stripe avec la clé du serveur :**

```javascript
// Dans static/js/stripe-init.js
async function initStripeFromServer() {
  try {
    const res = await fetch('/api/stripe-pk');
    if (!res.ok) {
      console.warn('Stripe publishable key not found on server');
      return null;
    }
    const json = await res.json();
    if (json.success && json.publishable_key) {
      window.STRIPE_PK = json.publishable_key;
      window.STRIPE = Stripe(window.STRIPE_PK);
      console.log('✅ Stripe initialisé');
      return window.STRIPE;
    } else {
      console.warn('No publishable key in response:', json);
      return null;
    }
  } catch (e) {
    console.error('initStripeFromServer error', e);
    return null;
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const stripe = await initStripeFromServer();
  if (stripe) {
    // Initialiser Elements / checkout
    console.log('Stripe prêt pour les paiements');
  } else {
    // Masquer formulaire / afficher message admin
    console.log('Stripe non configuré');
  }
});
```

### 4.3 Configuration de la Secret Key

La Secret Key doit être configurée de manière sécurisée :

#### Via variable d'environnement (recommandé)

```env
STRIPE_SECRET_KEY=sk_live_...
```

#### Via l'API Dashboard

```bash
curl -X PUT https://template.artworksdigital.fr/api/export/settings/stripe_secret_key \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value": "sk_live_..."}'
```

#### Dans le code

```python
# Chargement de la clé
STRIPE_SECRET_KEY = get_setting('stripe_secret_key') or os.getenv('STRIPE_SECRET_KEY')

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    print("✅ Stripe Secret Key configurée")
else:
    print("⚠️ Stripe Secret Key manquante")
```

---

## 💰 5. Configuration du Prix SAAS

### 5.1 Logique du Prix

Le Dashboard calcule le prix final pour chaque site :
```
Prix final = Prix de base × (1 + Commission %)
Exemple : 500€ × (1 + 10%) = 550€
```

### 5.2 Propagation depuis le Dashboard

**Côté Dashboard (Python) :**

```python
def configure_site_preview_price(site_url, base_price=500, commission_percent=10):
    """Configure le prix SAAS sur un site template"""
    final_price = base_price * (1 + commission_percent / 100)
    
    response = requests.put(
        f'{site_url}/api/export/settings/saas_site_price_cache',
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': 'template-master-key-2025'
        },
        json={'value': f'{final_price:.2f}'}
    )
    
    return response.json()

# Exemple d'utilisation
result = configure_site_preview_price(
    'https://template.artworksdigital.fr',
    base_price=500,
    commission_percent=10
)
print(result)  # {'success': True, 'message': '...'}
```

**Côté Dashboard (JavaScript) :**

```javascript
async function configureSitePreviewPrice(siteUrl, basePrice = 500, commissionPercent = 10) {
    const finalPrice = basePrice * (1 + commissionPercent / 100);
    
    const response = await fetch(
        `${siteUrl}/api/export/settings/saas_site_price_cache`,
        {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': 'template-master-key-2025'
            },
            body: JSON.stringify({
                value: finalPrice.toFixed(2)
            })
        }
    );
    
    const data = await response.json();
    
    if (data.success) {
        console.log(`✅ Prix configuré: ${finalPrice}€`);
    } else {
        console.error(`❌ Erreur: ${data.error}`);
    }
    
    return data;
}

// Exemple d'utilisation
configureSitePreviewPrice('https://template.artworksdigital.fr', 500, 10);
```

### 5.3 Affichage du Prix côté Template

Le Template affiche automatiquement le prix sur le bouton "Lancer mon site" :

```python
def is_preview_request():
    """Détecte si le site est en mode preview"""
    host = request.headers.get('Host', '').lower()
    return host == 'template.artworksdigital.fr' or host.startswith('preview-')

@app.route('/pricing')
def pricing():
    if is_preview_request():
        # Récupérer le prix configuré par le Dashboard
        price = get_setting('saas_site_price_cache') or '500.00'
        return render_template('pricing.html', saas_price=price)
    else:
        # Site en production, pas d'affichage du prix
        return render_template('pricing.html')
```

---

## 📦 6. Propagation en Masse

### 6.1 Script Python Synchrone

Pour pousser la configuration vers plusieurs sites :

```python
# dashboard_push_stripe_pk.py
import requests

TEMPLATE_MASTER_KEY = 'template-master-key-2025'
PUBLISHABLE_KEY = 'pk_live_...'

sites = [
    'https://site1.artworksdigital.fr',
    'https://site2.artworksdigital.fr',
    'https://site3.artworksdigital.fr',
]

for site in sites:
    url = f"{site.rstrip('/')}/api/export/settings/stripe_publishable_key"
    try:
        resp = requests.put(
            url,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': TEMPLATE_MASTER_KEY
            },
            json={'value': PUBLISHABLE_KEY},
            timeout=8
        )
        status = '✅' if resp.ok else '❌'
        print(f"{status} {site}: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ {site}: Erreur - {e}")
```

### 6.2 Script Python Asynchrone

Pour une propagation plus rapide en parallèle :

```python
# dashboard_push_stripe_pk_async.py
import asyncio
import aiohttp

TEMPLATE_MASTER_KEY = 'template-master-key-2025'
PUBLISHABLE_KEY = 'pk_live_...'

sites = [
    'https://site1.artworksdigital.fr',
    'https://site2.artworksdigital.fr',
    'https://site3.artworksdigital.fr',
]

async def push_to_site(session, site):
    url = f"{site.rstrip('/')}/api/export/settings/stripe_publishable_key"
    try:
        async with session.put(
            url,
            headers={
                'Content-Type': 'application/json',
                'X-API-Key': TEMPLATE_MASTER_KEY
            },
            json={'value': PUBLISHABLE_KEY},
            timeout=aiohttp.ClientTimeout(total=8)
        ) as resp:
            text = await resp.text()
            status = '✅' if resp.ok else '❌'
            print(f"{status} {site}: {resp.status} - {text}")
    except Exception as e:
        print(f"❌ {site}: Erreur - {e}")

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [push_to_site(session, site) for site in sites]
        await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 🧪 7. Tests et Validation

### 7.1 Test de la Clé Maître

```bash
# Test 1 : Vérifier le chargement de la variable
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('TEMPLATE_MASTER_API_KEY'))"
# Résultat attendu : template-master-key-2025

# Test 2 : Accès API avec clé maître
curl -X GET https://template.artworksdigital.fr/api/export/stats \
  -H "X-API-Key: template-master-key-2025"
# Résultat attendu : JSON avec les statistiques

# Test 3 : Mise à jour d'un paramètre
curl -X PUT https://template.artworksdigital.fr/api/export/settings/test_key \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value": "test_value"}'
# Résultat attendu : {"success": true}

# Test 4 : Vérifier que la mauvaise clé échoue
curl -X PUT https://template.artworksdigital.fr/api/export/settings/test_key \
  -H "Content-Type: application/json" \
  -H "X-API-Key: wrong-key" \
  -d '{"value": "test_value"}'
# Résultat attendu : {"error": "Clé API invalide"}, status 403
```

### 7.2 Test Stripe

```bash
# Test 1 : Vérifier la présence de la publishable key
curl -i https://template.artworksdigital.fr/api/stripe-pk
# Résultat attendu : {"success": true, "publishable_key": "pk_..."}

# Test 2 : Pousser une nouvelle publishable key
curl -X PUT https://template.artworksdigital.fr/api/export/settings/stripe_publishable_key \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value":"pk_test_51Hxxxx..."}'
# Résultat attendu : {"success": true}

# Test 3 : Vérifier la nouvelle clé
curl -i https://template.artworksdigital.fr/api/stripe-pk
# Résultat attendu : {"success": true, "publishable_key": "pk_test_51Hxxxx..."}
```

### 7.3 Test du Prix SAAS

```bash
# Test 1 : Configurer le prix
curl -X PUT https://template.artworksdigital.fr/api/export/settings/saas_site_price_cache \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value": "550.00"}'
# Résultat attendu : {"success": true}

# Test 2 : Vérifier le prix dans les settings
curl -X GET https://template.artworksdigital.fr/api/export/settings \
  -H "X-API-Key: template-master-key-2025"
# Chercher "saas_site_price_cache": "550.00" dans la réponse
```

### 7.4 Scripts de Test Automatisés

Des scripts de test sont fournis dans le repository :

```bash
# Test complet de l'API
python test_api.py

# Test de la clé maître
python test_master_api_key.py

# Test sur Scalingo (production)
python test_scalingo_api.py
```

---

## 🚀 8. Déploiement sur Scalingo

### 8.1 Configuration Initiale

**Étape 1 : Créer l'application**

```bash
scalingo create template-artworksdigital
```

**Étape 2 : Ajouter la base de données**

```bash
scalingo --app template-artworksdigital addons-add postgresql postgresql-starter-1024
```

**Étape 3 : Configurer les variables d'environnement**

Via l'interface Scalingo ou en ligne de commande :

```bash
scalingo --app template-artworksdigital env-set \
  TEMPLATE_MASTER_API_KEY=template-master-key-2025 \
  SECRET_KEY=your-very-long-random-secret-key \
  FLASK_ENV=production
```

**Étape 4 : Déployer**

```bash
git remote add scalingo git@ssh.osc-fr1.scalingo.com:template-artworksdigital.git
git push scalingo main
```

### 8.2 Vérification du Déploiement

**Consulter les logs :**

```bash
scalingo --app template-artworksdigital logs -f
```

Vous devriez voir :
```
🔑 Clé maître dashboard chargée: template-ma...y-2025
✅ Stripe Secret Key configurée
* Running on http://0.0.0.0:5000/
```

**Tester l'application :**

```bash
curl https://template-artworksdigital.osc-fr1.scalingo.io/api/export/stats \
  -H "X-API-Key: template-master-key-2025"
```

---

## 🔄 9. Workflow Complet Dashboard → Template

### 9.1 Scénario : Création d'un nouveau site artiste

1. **Dashboard** : L'artiste crée son compte sur le dashboard
2. **Dashboard** : Génère un sous-domaine unique (ex: `artiste123.artworksdigital.fr`)
3. **Dashboard** : Clone/déploie le template sur ce sous-domaine
4. **Dashboard** : Configure automatiquement le site via l'API :
   ```javascript
   // Configurer la publishable key
   await fetch(`${siteUrl}/api/export/settings/stripe_publishable_key`, {
     method: 'PUT',
     headers: {
       'Content-Type': 'application/json',
       'X-API-Key': 'template-master-key-2025'
     },
     body: JSON.stringify({ value: 'pk_live_...' })
   });
   
   // Configurer le prix SAAS
   await fetch(`${siteUrl}/api/export/settings/saas_site_price_cache`, {
     method: 'PUT',
     headers: {
       'Content-Type': 'application/json',
       'X-API-Key': 'template-master-key-2025'
     },
     body: JSON.stringify({ value: '550.00' })
   });
   ```
5. **Template** : Sauvegarde les configurations en base de données
6. **Template** : Affiche le prix sur le bouton "Lancer mon site"
7. **Artiste** : Visite son site en preview, voit le prix, clique sur "Lancer mon site"
8. **Template** : Crée une session Stripe et redirige vers le paiement
9. **Stripe** : L'artiste effectue le paiement
10. **Dashboard** : Reçoit le webhook Stripe de confirmation
11. **Dashboard** : Active le site en production (désactive le mode preview)
12. **Artiste** : Le site est maintenant live !

### 9.2 Diagramme de Séquence

```
Artiste          Dashboard              Template              Stripe
   |                 |                      |                   |
   |--- Inscription->|                      |                   |
   |                 |                      |                   |
   |                 |--- Clone/Deploy ---->|                   |
   |                 |                      |                   |
   |                 |--- Config API ------>|                   |
   |                 |  (PK, SK, Prix)      |                   |
   |                 |                      |                   |
   |                 |<----- Success -------|                   |
   |                 |                      |                   |
   |<-- Email Preview URL ----------------- |                   |
   |                 |                      |                   |
   |-------------- Visite Site ------------>|                   |
   |                 |                      |                   |
   |<----------- Affichage Prix ------------|                   |
   |                 |                      |                   |
   |---- Clic "Lancer mon site" ----------->|                   |
   |                 |                      |                   |
   |                 |                      |--- Create Session ->|
   |                 |                      |                   |
   |<----------- Redirect Stripe -----------|<-- Session URL ---|
   |                 |                      |                   |
   |-------------- Paiement ------------------------------->|
   |                 |                      |                   |
   |                 |<----------- Webhook Confirmation --------|
   |                 |                      |                   |
   |                 |--- Active Site ----->|                   |
   |                 |                      |                   |
   |<-- Email Confirmation ----------------|                   |
   |                 |                      |                   |
```

---

## 🔐 10. Sécurité

### 10.1 Bonnes Pratiques

✅ **À FAIRE :**
- Stocker toutes les clés sensibles dans des variables d'environnement
- Ajouter `.env` dans `.gitignore`
- Utiliser HTTPS en production (obligatoire)
- Logger toutes les modifications via l'API
- Valider strictement les headers HTTP (`X-API-Key`)
- Masquer les clés sensibles dans les exports (`GET /api/export/settings`)
- Limiter les tentatives de connexion (rate limiting)
- Utiliser des clés longues et aléatoires

❌ **À ÉVITER :**
- Clés en dur dans le code source
- Clés committées sur Git
- HTTP en production
- Exposer la secret key côté client
- Pas de validation des paramètres d'entrée
- Logs contenant des clés complètes

### 10.2 Structure des Clés

```env
# ❌ MAUVAIS : Clés faibles
TEMPLATE_MASTER_API_KEY=123
STRIPE_SECRET_KEY=sk_test_123

# ✅ BON : Clés fortes et sécurisées
TEMPLATE_MASTER_API_KEY=template-master-key-2025-7f9a8c3e2d1b
STRIPE_SECRET_KEY=[Utilisez votre vraie clé Stripe sk_live_... ou sk_test_...]
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0
```

### 10.3 Protection des Endpoints

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/export/settings/<key>', methods=['PUT'])
@limiter.limit("10 per minute")
def update_setting_api(key):
    # Votre code ici
    pass
```

---

## 📚 11. Variables d'Environnement Complètes

### 11.1 Variables Obligatoires

```env
# Clé API maître (OBLIGATOIRE pour intégration dashboard)
TEMPLATE_MASTER_API_KEY=template-master-key-2025

# Flask (OBLIGATOIRE)
SECRET_KEY=your-very-long-random-secret-key
FLASK_ENV=production

# Base de données (OBLIGATOIRE en production)
DATABASE_URL=postgresql://user:pass@host:5432/db
```

### 11.2 Variables Optionnelles

```env
# Stripe (optionnel, peut être configuré via API)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# SMTP (optionnel, peut être dans settings)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=contact@example.com
SMTP_PASSWORD=app_password

# Dashboard (optionnel, pour fallback server→server)
DASHBOARD_URL=https://admin.artworksdigital.fr
SITE_NAME=template
```

### 11.3 Exemple de fichier `.env.example`

```env
# Clé API maître pour authentification Dashboard
TEMPLATE_MASTER_API_KEY=template-master-key-2025

# Flask
SECRET_KEY=change-me-to-a-random-secret-key
FLASK_ENV=development

# Base de données (PostgreSQL en production, SQLite en local)
DATABASE_URL=sqlite:///app.db

# Stripe (optionnel)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# SMTP (optionnel)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Dashboard (optionnel)
DASHBOARD_URL=
SITE_NAME=
```

---

## 🐛 12. Dépannage

### 12.1 Erreurs Courantes

#### Erreur 403 : "Clé API invalide"

**Symptômes :**
```json
{"error": "Clé API invalide"}
```

**Solutions :**
1. Vérifiez que la variable `TEMPLATE_MASTER_API_KEY` est définie sur Scalingo
2. Vérifiez le header : `X-API-Key` (pas `Authorization`)
3. Vérifiez la valeur : `template-master-key-2025` (pas d'espace, majuscules/minuscules)
4. Redémarrez l'application après avoir ajouté la variable

**Test :**
```bash
curl -X GET https://template.artworksdigital.fr/api/export/stats \
  -H "X-API-Key: template-master-key-2025" \
  -v
```

#### Erreur 404 : "no_publishable_key"

**Symptômes :**
```json
{"success": false, "message": "no_publishable_key"}
```

**Solutions :**
1. Configurez la publishable key via l'API :
   ```bash
   curl -X PUT https://template.artworksdigital.fr/api/export/settings/stripe_publishable_key \
     -H "Content-Type: application/json" \
     -H "X-API-Key: template-master-key-2025" \
     -d '{"value":"pk_test_..."}'
   ```
2. Ou définissez la variable d'environnement `STRIPE_PUBLISHABLE_KEY`

#### Erreur 500 : Erreur serveur

**Symptômes :**
```json
{"error": "Internal server error"}
```

**Solutions :**
1. Consultez les logs Scalingo : `scalingo --app template logs -f`
2. Cherchez les lignes avec `[API] ❌` ou `ERROR`
3. Vérifiez que la base de données est accessible
4. Vérifiez que toutes les dépendances sont installées

### 12.2 Le prix ne s'affiche pas

**Vérifications :**
1. Le paramètre existe en base de données :
   ```bash
   curl -X GET https://template.artworksdigital.fr/api/export/settings \
     -H "X-API-Key: template-master-key-2025" | grep saas_site_price_cache
   ```
2. La fonction `is_preview_request()` retourne `True` :
   - Vérifiez le domaine : doit être `template.artworksdigital.fr` ou `preview-*`
3. Le template utilise bien la variable `{{ saas_price }}`

### 12.3 Stripe ne fonctionne pas

**Vérifications :**
1. La publishable key est accessible :
   ```bash
   curl https://template.artworksdigital.fr/api/stripe-pk
   ```
2. Stripe.js est chargé :
   ```html
   <script src="https://js.stripe.com/v3/"></script>
   ```
3. La console JavaScript ne contient pas d'erreurs :
   - Ouvrir DevTools (F12) > Console
   - Chercher les messages d'erreur Stripe

### 12.4 Logs Utiles

**Consulter les logs en temps réel :**
```bash
scalingo --app template logs -f
```

**Filtrer les logs API :**
```bash
scalingo --app template logs | grep "[API]"
```

**Filtrer les erreurs :**
```bash
scalingo --app template logs | grep -E "(ERROR|❌)"
```

---

## 📖 13. Documentation Complémentaire

### 13.1 Fichiers du Repository

| Fichier | Description |
|---------|-------------|
| `TEMPLATE_INTEGRATION_GUIDE.md` | **Ce guide** - Guide complet d'intégration |
| `TEMPLATE_API_SETUP.md` | Configuration détaillée de la clé API maître |
| `TEMPLATE_STRIPE_INTEGRATION.md` | Intégration Stripe (publishable key) |
| `DASHBOARD_PUSH_INSTRUCTIONS.md` | Instructions de propagation depuis le dashboard |
| `RESUME_INTEGRATION_DASHBOARD.md` | Résumé de l'intégration dashboard |
| `SCALINGO_DEPLOYMENT.md` | Guide de déploiement Scalingo |
| `STRIPE_SECRET_KEY_AUTO_PROPAGATION.md` | Propagation automatique de la secret key |
| `.env.example` | Exemple de configuration des variables d'environnement |

### 13.2 Scripts Utiles

| Script | Description |
|--------|-------------|
| `dashboard_push_stripe_pk.py` | Script synchrone de propagation (Stripe PK) |
| `dashboard_push_stripe_pk_async.py` | Script asynchrone de propagation (Stripe PK) |
| `dashboard_push_stripe_sk.py` | Script synchrone de propagation (Stripe SK) |
| `dashboard_push_stripe_sk_async.py` | Script asynchrone de propagation (Stripe SK) |
| `test_api.py` | Tests unitaires de l'API |
| `test_master_api_key.py` | Tests de la clé maître |
| `test_scalingo_api.py` | Tests sur l'environnement Scalingo |

### 13.3 Ressources Externes

- [Documentation Flask](https://flask.palletsprojects.com/)
- [Documentation Stripe](https://stripe.com/docs)
- [Documentation Scalingo](https://doc.scalingo.com/)
- [Best Practices API REST](https://restfulapi.net/)

---

## ✅ 14. Checklist de Déploiement

### 14.1 Avant le Déploiement

- [ ] `.env` est dans `.gitignore`
- [ ] Toutes les clés sensibles sont en variables d'environnement
- [ ] Les dépendances sont à jour (`requirements.txt`)
- [ ] Les tests passent en local (`python test_api.py`)
- [ ] La base de données est migrée
- [ ] Stripe est configuré (mode test)

### 14.2 Sur Scalingo

- [ ] Application créée
- [ ] Base de données PostgreSQL ajoutée
- [ ] Variables d'environnement configurées :
  - [ ] `TEMPLATE_MASTER_API_KEY`
  - [ ] `SECRET_KEY`
  - [ ] `FLASK_ENV=production`
  - [ ] `DATABASE_URL` (auto)
- [ ] Code déployé (`git push scalingo main`)
- [ ] Logs vérifiés (pas d'erreurs)

### 14.3 Tests Post-Déploiement

- [ ] API accessible : `GET /api/export/stats`
- [ ] Clé maître fonctionne : test avec `curl`
- [ ] Stripe PK accessible : `GET /api/stripe-pk`
- [ ] Configuration fonctionne : test `PUT /api/export/settings/*`
- [ ] Interface web accessible
- [ ] Certificat SSL actif (HTTPS)

### 14.4 Intégration Dashboard

- [ ] Dashboard connaît l'URL du template
- [ ] Dashboard a la clé maître
- [ ] Dashboard peut pousser la publishable key
- [ ] Dashboard peut configurer le prix
- [ ] Workflow complet testé (création → preview → paiement → activation)

---

## 🎉 15. Résultat Final

Une fois l'intégration complète, vous disposez de :

✅ **Un système centralisé** : Le Dashboard gère tous les sites d'artistes depuis une interface unique

✅ **Une configuration automatique** : Nouveau site = configuration instantanée (prix, Stripe, etc.)

✅ **Une sécurité renforcée** : Clé maître partagée, HTTPS, validation stricte

✅ **Un workflow optimisé** :
- Artiste s'inscrit → Dashboard crée le site
- Dashboard configure → Template prêt
- Artiste preview → Validation
- Artiste paye → Site activé
- Tout est automatique ! 🚀

✅ **Une scalabilité** : Ajoutez autant de sites que nécessaire sans intervention manuelle

---

## 📞 16. Support

### Questions Fréquentes

**Q : Puis-je utiliser une clé différente pour chaque site ?**
R : Oui, mais ce n'est pas recommandé. La clé maître permet une gestion centralisée. Pour des besoins spécifiques, utilisez la clé locale `export_api_key`.

**Q : Comment changer la clé maître ?**
R : 
1. Mettez à jour la variable `TEMPLATE_MASTER_API_KEY` sur tous les sites
2. Mettez à jour le Dashboard avec la nouvelle clé
3. Redémarrez les applications

**Q : Le Dashboard doit-il être dans le même réseau que les Templates ?**
R : Non, la communication se fait via HTTPS sur Internet. Assurez-vous que les sites sont accessibles publiquement.

**Q : Combien de sites puis-je gérer ?**
R : Il n'y a pas de limite technique. La clé maître fonctionne pour un nombre illimité de sites.

### Contacts

- **Issues GitHub** : [Colin-tech-VS/Template/issues](https://github.com/Colin-tech-VS/Template/issues)
- **Documentation** : Ce fichier et les autres fichiers `.md` du repository

---

**Version :** 1.0  
**Date :** Décembre 2024  
**Statut :** ✅ Production Ready
