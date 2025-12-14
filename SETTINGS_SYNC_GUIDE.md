# Guide: Synchronisation des Settings Template → Dashboard

## 📊 Question 1: Comment les données des settings sont envoyées au Dashboard?

### Flow de synchronisation:

```
Admin Settings (Template)
         ↓
   Base de données (table: settings)
         ↓
   GET /api/export/settings (API avec X-API-Key)
         ↓
   Dashboard (récupère via HTTP)
         ↓
   Base de données Dashboard
```

---

## ✅ Points clés pour que ça marche:

### 1️⃣ **Le Template expose l'API** ✓ (déjà en place)

```python
# app.py:4032 - Endpoint API
@app.route('/api/export/settings', methods=['GET'])
@require_api_key
def api_export_settings():
    # Retourne tous les settings en JSON
    # Masque les clés sensibles (stripe_secret_key, smtp_password)
```

**Résultat HTTP 200**:
```json
{
  "success": true,
  "count": 35,
  "data": [
    {"id": 1, "key": "primary_color", "value": "#1E3A8A"},
    {"id": 2, "key": "secondary_color", "value": "#3B65C4"},
    {"id": 3, "key": "site_name", "value": "Jean-Baptiste Art"},
    ...
  ]
}
```

---

### 2️⃣ **L'authentification API fonctionne** ✓ (déjà en place)

Le Template utilise `TEMPLATE_MASTER_API_KEY`:

```python
# app.py:86
TEMPLATE_MASTER_API_KEY = os.getenv('TEMPLATE_MASTER_API_KEY')

# app.py:614 - Vérification du header X-API-Key
@wraps(f)
def decorated(*args, **kwargs):
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return jsonify({"error": "invalid_api_key"}), 401
    
    # Vérification constante-temps contre la clé maître
    ok_master = hmac.compare_digest(api_key, TEMPLATE_MASTER_API_KEY)
    
    if not ok_master:
        return jsonify({"error": "invalid_api_key"}), 401
```

**Configuration requise**:
```bash
# Sur le serveur Template (Scalingo):
scalingo -a template-production env-set \
  TEMPLATE_MASTER_API_KEY="sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW"

# Sur le Dashboard (Scalingo):
scalingo -a dashboard-production env-set \
  TEMPLATE_API_KEY="sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW"
  
# Les deux DOIVENT être identiques!
```

---

### 3️⃣ **Le Dashboard récupère les settings**

Le Dashboard doit faire une requête HTTP:

```python
# Dans le Dashboard:
import requests

TEMPLATE_URL = os.getenv('TEMPLATE_BASE_URL')  # "https://example.artworksdigital.fr"
API_KEY = os.getenv('TEMPLATE_API_KEY')

response = requests.get(
    f"{TEMPLATE_URL}/api/export/settings",
    headers={"X-API-Key": API_KEY},
    timeout=30
)

if response.status_code == 200:
    settings = response.json()['data']
    for setting in settings:
        # Sauvegarder dans la base Dashboard
        save_setting(setting['key'], setting['value'])
else:
    print(f"Erreur: {response.status_code} - {response.json()}")
```

---

### 4️⃣ **Les settings sont stockés en base de données**

Table `settings` sur Template:
```sql
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL
);

-- Exemples:
INSERT INTO settings (key, value) VALUES ('primary_color', '#1E3A8A');
INSERT INTO settings (key, value) VALUES ('secondary_color', '#3B65C4');
INSERT INTO settings (key, value) VALUES ('site_name', 'Jean-Baptiste Art');
INSERT INTO settings (key, value) VALUES ('smtp_password', 'secret123');
```

⚠️ **Important**: Toute modification dans Admin Settings doit:
1. Mettre à jour la table `settings`
2. Être disponible immédiatement via `/api/export/settings`

---

### 5️⃣ **Les settings sensibles sont masqués**

L'API masque automatiquement:
- `stripe_secret_key` → `***MASKED***`
- `smtp_password` → `***MASKED***`
- `export_api_key` → `***MASKED***`

**Code (app.py:4043)**:
```python
sensitive_keys = ['stripe_secret_key', 'smtp_password', 'export_api_key']

for setting in settings:
    if setting['key'] in sensitive_keys:
        setting['value'] = '***MASKED***'
```

---

### 6️⃣ **Format standard des settings**

Chaque setting doit avoir:
- `id`: INTEGER (autoincrement)
- `key`: TEXT UNIQUE (ex: "primary_color")
- `value`: TEXT (ex: "#1E3A8A")

**Structure recommandée**:
```json
{
  "key": "primary_color",
  "value": "#1E3A8A"
}
```

---

## 🔴 Question 2: Pourquoi les couleurs ne s'appliquent pas?

### Problème identifié:

Le CSS dynamique (`/dynamic-colors.css`) génère des variables CSS `:root`, mais les éléments HTML ne les utilisent **PAS**.

**Code actuel (app.py:3804-3819)**:
```css
:root {
    --color-primary: #1E3A8A;
    --color-secondary: #3B65C4;
    --color-accent: #FF7F50;
}

* {
    --color-primary: #1E3A8A !important;
    --color-secondary: #3B65C4 !important;
    --color-accent: #FF7F50 !important;
}
```

❌ **Problème**: Les variables CSS existent mais le CSS statique (`style.css`) ne les utilise pas!

### Solution: Appliquer directement les couleurs aux éléments

Modifier `/dynamic-colors.css` pour appliquer les couleurs:

```python
# app.py:3792-3825
@app.route('/dynamic-colors.css')
def dynamic_colors():
    """Génère dynamiquement le CSS des couleurs du site"""
    try:
        color_primary = get_setting("primary_color") or "#1E3A8A"
        color_secondary = get_setting("secondary_color") or "#3B65C4"
        accent_color = get_setting("accent_color") or "#FF7F50"
        button_text_color = get_setting("button_text_color") or "#FFFFFF"
        content_text_color = get_setting("content_text_color") or "#000000"
        button_hover_color = get_setting("button_hover_color") or "#9C27B0"
        
        css = f"""
        /* Variables CSS */
        :root {{
            --color-primary: {color_primary};
            --color-secondary: {color_secondary};
            --color-accent: {accent_color};
            --button-text-color: {button_text_color};
            --content-text-color: {content_text_color};
            --button-hover-color: {button_hover_color};
        }}
        
        /* Forcer les couleurs avec !important sur les éléments courants */
        a {{
            color: {color_primary} !important;
        }}
        
        button, [type="button"], [type="submit"] {{
            background-color: {color_primary} !important;
            color: {button_text_color} !important;
        }}
        
        button:hover, [type="button"]:hover, [type="submit"]:hover {{
            background-color: {button_hover_color} !important;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: {color_primary} !important;
        }}
        
        .nav, nav, .navbar {{
            background-color: {color_secondary} !important;
        }}
        
        .btn-primary, .primary {{
            background-color: {color_primary} !important;
            color: {button_text_color} !important;
        }}
        
        .btn-primary:hover, .primary:hover {{
            background-color: {button_hover_color} !important;
        }}
        
        body {{
            color: {content_text_color} !important;
        }}
        """
        
        response = make_response(css)
        response.mimetype = 'text/css'
        # ⭐ IMPORTANT: Empêcher le cache navigateur
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, public, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        print(f"[DYNAMIC_COLORS] Erreur: {e}")
        return "", 500
```

---

## 🔧 Checklist: Pourquoi les couleurs ne s'appliquent PAS?

```
☐ La couleur est sauvegardée en base (SELECT * FROM settings WHERE key='primary_color')
☐ La couleur est exposée via l'API (GET /api/export/settings)
☐ Le fichier /dynamic-colors.css est inclus dans <head>
  ✓ Vérifier: <link rel="stylesheet" href="{{ url_for('dynamic_colors') }}">
☐ Le CSS dynamique génère les variables
☐ Les éléments HTML UTILISENT les variables
  ❌ Problème: style.css utilise des couleurs hardcodées au lieu de --color-primary
☐ Pas de cache navigateur (F12 > Network > voir les headers Cache-Control)
☐ Pas de conflit CSS (autres règles avec plus de spécificité)
```

---

## 🔄 Test complet du flow:

```bash
# 1. Vérifier que la couleur existe en base
sqlite3 template.db "SELECT key, value FROM settings WHERE key LIKE '%color%'"

# 2. Tester l'API
curl -H "X-API-Key: sk_..." https://example.artworksdigital.fr/api/export/settings | jq '.data[] | select(.key == "primary_color")'

# 3. Tester le CSS dynamique
curl -i https://example.artworksdigital.fr/dynamic-colors.css | head -20

# 4. Vérifier que le CSS est inclus dans le HTML
curl https://example.artworksdigital.fr | grep "dynamic-colors"

# 5. Sur le navigateur (F12 > Elements > Inspect > Styles)
# Vérifier que la variable CSS est appliquée
```

---

## ✅ Solution complète: Checklist de fix

### Étape 1: Vérifier les headers no-cache
```python
# Ajouter dans dynamic_colors():
response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
response.headers['Pragma'] = 'no-cache'
response.headers['Expires'] = '0'
```

### Étape 2: Appliquer les couleurs directement aux éléments
```css
/* Dans /dynamic-colors.css, ajouter: */
button, a.btn { background: var(--color-primary) !important; }
h1, h2, h3 { color: var(--color-primary) !important; }
nav { background: var(--color-secondary) !important; }
```

### Étape 3: Tester localement
```bash
# Modifier une couleur dans Admin Settings
# F5 (refresh sans cache)
# Vérifier que la couleur a changé immédiatement
```

### Étape 4: Redéployer
```bash
git add -A
git commit -m "Fix: Apply dynamic colors to DOM elements"
git push
scalingo -a template-production deploy
```

---

## 📝 Résumé final

| Aspect | État | Action |
|--------|------|--------|
| **API Settings** | ✅ Fonctionne | Rien à faire |
| **Authentification API** | ✅ Fonctionne | Vérifier les clés |
| **Stockage Settings** | ✅ Fonctionne | Rien à faire |
| **CSS Dynamique** | ❌ Ne s'applique pas | Ajouter règles CSS + no-cache |
| **Dashboard Sync** | À documenter | Créer client Python |

