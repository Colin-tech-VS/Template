# Troubleshooting 401 Unauthorized - Template API

## ❌ Le Problème
Votre Dashboard reçoit une erreur **401 Unauthorized** en essayant d'appeler `/api/export/settings` sur le Template distant.

```
HTTP/1.1 401 Unauthorized
{
  "error": "invalid_api_key",
  "success": false
}
```

---

## ✅ Solutions - Checklist Ordonnée

### 1️⃣ Vérifier que le header X-API-Key est présent

**❌ Mauvais**:
```bash
curl https://example.artworksdigital.fr/api/export/settings
```

**✅ Correct**:
```bash
curl -H "X-API-Key: sk-abc123def456" \
  https://example.artworksdigital.fr/api/export/settings
```

**En Python**:
```python
import requests

headers = {
    "X-API-Key": "sk-abc123def456"  # ← IMPORTANT
}

response = requests.get(
    "https://example.artworksdigital.fr/api/export/settings",
    headers=headers
)
```

---

### 2️⃣ Vérifier que la clé API est correcte

#### Sur le serveur Template:

```bash
# SSH vers le Template (ex: Scalingo)
scalingo -a template-production env

# Chercher TEMPLATE_MASTER_API_KEY
# Exemple de sortie:
# TEMPLATE_MASTER_API_KEY=sk_prod_abc123def456789xyz...
```

#### Si la clé n'existe pas:

**Générer une nouvelle clé sécurisée**:
```bash
# Option 1: Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Option 2: OpenSSL
openssl rand -base64 32

# Option 3: Utiliser un UUID
python3 -c "import uuid; print(str(uuid.uuid4()) + str(uuid.uuid4()))"
```

**Exemple de sortie**:
```
sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW
```

#### Sur Scalingo:

```bash
# Voir toutes les variables
scalingo -a template-production env

# Ajouter la nouvelle clé
scalingo -a template-production env-set TEMPLATE_MASTER_API_KEY="sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW"

# Redémarrer l'app
scalingo -a template-production restart
```

---

### 3️⃣ Copier la clé exactement du Dashboard

**Sur le Dashboard (Scalingo)**:

```bash
# Voir la clé stockée
scalingo -a dashboard-production env | grep TEMPLATE_API_KEY

# Ou en manuellement si elle n'existe pas
scalingo -a dashboard-production env-set TEMPLATE_API_KEY="sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW"
```

**Vérifier qu'elle est identique sur les deux serveurs**:
```bash
# Template
scalingo -a template-production env | grep TEMPLATE_MASTER_API_KEY

# Dashboard
scalingo -a dashboard-production env | grep TEMPLATE_API_KEY

# Les valeurs DOIVENT être identiques
```

---

### 4️⃣ Tester avec cURL avant de coder

```bash
# Test simple
curl -H "X-API-Key: sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW" \
  https://example.artworksdigital.fr/api/export/settings

# Test avec verbose pour voir les headers
curl -v -H "X-API-Key: sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW" \
  https://example.artworksdigital.fr/api/export/settings

# Test avec jq pour formater la réponse
curl -s -H "X-API-Key: sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW" \
  https://example.artworksdigital.fr/api/export/settings | jq .
```

**Réponse attendue (200 OK)**:
```json
{
  "success": true,
  "count": 35,
  "data": [
    {
      "id": 1,
      "key": "primary_color",
      "value": "#1E3A8A"
    }
  ]
}
```

**Réponse erreur (401)**:
```json
{
  "error": "invalid_api_key",
  "success": false
}
```

---

### 5️⃣ Utiliser le script de test fourni

#### Python:
```bash
python3 test_api.py "https://example.artworksdigital.fr" "sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW"
```

#### Bash:
```bash
chmod +x test_api.sh
./test_api.sh "https://example.artworksdigital.fr" "sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW"
```

---

### 6️⃣ Vérifier les logs du Template

**Logs locaux** (si vous avez accès au serveur):
```bash
tail -f logs/app.log | grep -i "api_key\|401\|unauthorized"
```

**Sur Scalingo**:
```bash
scalingo -a template-production logs | tail -100 | grep -i "api_key\|401"
```

**Chercher les messages d'erreur de l'API**:
```python
# Exemple dans app.py:
print(f"[API_KEY] Reçu: {api_key}")
print(f"[API_KEY] Attendu: {TEMPLATE_MASTER_API_KEY}")
print(f"[API_KEY] Match: {api_key == TEMPLATE_MASTER_API_KEY}")
```

---

### 7️⃣ Vérifier que CORS n'est pas le problème

**Si le Dashboard est en HTTPS et le Template aussi**, vérifier les CORS headers:

```bash
curl -i -H "Origin: https://dashboard.com" \
  -H "X-API-Key: sk_..." \
  https://example.artworksdigital.fr/api/export/settings
```

**Réponse doit contenir**:
```
Access-Control-Allow-Origin: *
```

**Si manquant, ajouter dans Flask**:
```python
from flask_cors import CORS

CORS(app)  # Ou configurer spécifiquement
```

---

### 8️⃣ Vérifier les certificats SSL (HTTPS)

```bash
# Vérifier que le certificat est valide
curl -vI https://example.artworksdigital.fr/api/export/settings 2>&1 | grep -i "certificate\|verify\|ssl"

# Forcer la vérification
curl --insecure -H "X-API-Key: sk_..." \
  https://example.artworksdigital.fr/api/export/settings

# Si ça marche avec --insecure, le problème est le certificat SSL
```

**En Python**:
```python
import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

response = requests.get(
    "https://example.artworksdigital.fr/api/export/settings",
    headers={"X-API-Key": "sk_..."},
    verify=False  # Ignorer la vérification SSL (⚠️ DEV ONLY)
)
```

---

## 🔍 Checklist de Dépannage Complète

```
Pour chaque erreur 401, cocher les points:

Template (Serveur)
☐ TEMPLATE_MASTER_API_KEY est définie en variable d'environnement
☐ TEMPLATE_MASTER_API_KEY a une valeur non-vide
☐ La clé API n'a pas d'espaces ou caractères invisibles
☐ L'app a été redémarrée après changement de variable d'env
☐ get_setting('export_api_key') retourne None ou une clé valide

Dashboard (Client)
☐ TEMPLATE_API_KEY est défini avec la MÊME valeur que Template
☐ Le code utilise headers={'X-API-Key': TEMPLATE_API_KEY}
☐ La clé API n'a pas d'espaces ou caractères invisibles
☐ requests.get() reçoit headers=headers

Réseau
☐ Vérifier la connectivité: ping example.artworksdigital.fr
☐ Vérifier l'URL est correcte (https://, pas de trailing slash)
☐ Certificat SSL valide (si HTTPS)
☐ CORS configuré si fetch depuis navigateur

Code
☐ Lire les logs pour voir la clé reçue vs attendue
☐ Ajouter debug print pour voir le header envoyé
☐ Vérifier que la clé n'est pas coupée ou modifiée
```

---

## 🛠️ Exemple Complet de Débogage

```python
import requests
import os

# 1. Afficher ce qu'on va envoyer
TEMPLATE_URL = "https://example.artworksdigital.fr"
API_KEY = os.getenv('TEMPLATE_API_KEY')

print(f"URL: {TEMPLATE_URL}")
print(f"API_KEY: {API_KEY}")
print(f"API_KEY type: {type(API_KEY)}")
print(f"API_KEY length: {len(API_KEY) if API_KEY else 'None'}")

# 2. Vérifier les espaces
if API_KEY:
    print(f"Stripped match: {API_KEY.strip() != API_KEY}")
    API_KEY = API_KEY.strip()

# 3. Construire les headers
headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}
print(f"Headers: {headers}")

# 4. Faire la requête avec détails
try:
    print("\n📍 Sending request...")
    response = requests.get(
        f"{TEMPLATE_URL}/api/export/settings",
        headers=headers,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 401:
        print("\n❌ 401 Unauthorized - API key is invalid or missing")
        print("Checklist:")
        print("  1. Is TEMPLATE_MASTER_API_KEY set on Template server?")
        print("  2. Is it the SAME as TEMPLATE_API_KEY on Dashboard?")
        print("  3. Check for leading/trailing whitespace")
        print("  4. Restart Template app after changing variable")
    else:
        data = response.json()
        print(f"\n✅ Success! Got {data.get('count', 0)} settings")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
```

---

## 📞 Si rien ne marche

1. **Vérifier les logs complets**:
   ```bash
   scalingo -a template-production logs --lines=200
   ```

2. **Redémarrer l'app Template**:
   ```bash
   scalingo -a template-production restart
   ```

3. **Régénérer la clé API**:
   ```bash
   # Générer nouvelle clé
   NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
   
   # Ajouter sur Template
   scalingo -a template-production env-set TEMPLATE_MASTER_API_KEY="$NEW_KEY"
   
   # Ajouter sur Dashboard
   scalingo -a dashboard-production env-set TEMPLATE_API_KEY="$NEW_KEY"
   
   # Redémarrer les deux
   scalingo -a template-production restart
   scalingo -a dashboard-production restart
   ```

4. **Tester directement sur le serveur Template**:
   ```bash
   # SSH sur Template
   scalingo -a template-production run bash
   
   # Vérifier que la variable existe
   echo $TEMPLATE_MASTER_API_KEY
   
   # Tester l'endpoint localement
   curl -H "X-API-Key: $TEMPLATE_MASTER_API_KEY" \
     http://localhost:5000/api/export/settings
   ```

