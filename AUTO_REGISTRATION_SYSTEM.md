# 🔄 Système d'Auto-Registration au Dashboard Central

## Vue d'ensemble

Le template s'enregistre **automatiquement** sur le dashboard central (`mydashboard-v39e.onrender.com`) au premier démarrage.

---

## 🚀 Fonctionnement

### 1. Au démarrage du site template

```python
# Au lancement de app.py
1. Vérifie si une API key existe
2. Si non → Génère une clé API unique (secrets.token_urlsafe(32))
3. Vérifie si déjà enregistré sur le dashboard
4. Si non → Envoie automatiquement les infos au dashboard central
```

### 2. Données envoyées au dashboard

```json
POST https://mydashboard-v39e.onrender.com/api/sites/register
{
  "site_name": "Nom du site (depuis settings)",
  "site_url": "https://site-artiste.onrender.com",
  "api_key": "clé_générée_automatiquement",
  "auto_registered": true
}
```

### 3. Réponse du dashboard

```json
{
  "success": true,
  "site_id": "abc123",
  "message": "Site enregistré avec succès"
}
```

Le `site_id` est stocké localement dans `settings.dashboard_id`.

---

## 📋 Endpoint du Dashboard Central à créer

### Sur `mydashboard-v39e.onrender.com`

```python
@app.route('/api/sites/register', methods=['POST'])
def register_site():
    """
    Reçoit les informations d'un nouveau site template
    et l'ajoute à la liste des sites gérés
    """
    data = request.get_json()
    
    site_name = data.get('site_name')
    site_url = data.get('site_url')
    api_key = data.get('api_key')
    auto_registered = data.get('auto_registered', False)
    
    # Validation
    if not all([site_name, site_url, api_key]):
        return jsonify({'success': False, 'error': 'Missing data'}), 400
    
    # Vérifier si le site existe déjà (par URL)
    existing_site = Site.query.filter_by(url=site_url).first()
    
    if existing_site:
        # Mettre à jour l'API key si elle a changé
        existing_site.api_key = api_key
        existing_site.last_sync = datetime.now()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'site_id': existing_site.id,
            'message': 'Site mis à jour'
        })
    
    # Créer un nouveau site
    new_site = Site(
        name=site_name,
        url=site_url,
        api_key=api_key,
        status='active',
        auto_registered=auto_registered,
        created_at=datetime.now(),
        last_sync=datetime.now()
    )
    
    db.session.add(new_site)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'site_id': new_site.id,
        'message': 'Site enregistré avec succès'
    })
```

---

## 🗄️ Structure de la table Sites (Dashboard Central)

```sql
CREATE TABLE sites (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) UNIQUE NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    auto_registered BOOLEAN DEFAULT FALSE,
    artist_id INTEGER,  -- Lien avec l'artiste associé
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync TIMESTAMP,
    
    FOREIGN KEY (artist_id) REFERENCES artists(id)
);
```

---

## 🔧 Configuration du Template

### Variables d'environnement (optionnelles)

```bash
# .env ou configuration Render
SITE_URL=https://mon-site-artiste.onrender.com
```

Si `SITE_URL` n'est pas définie, le système utilise `request.url_root`.

---

## 📡 Endpoint de synchronisation manuelle

Si besoin de forcer une re-synchronisation :

```bash
POST /api/sync-dashboard
```

Exemple :
```bash
curl -X POST https://site-artiste.onrender.com/api/sync-dashboard
```

---

## 🎯 Workflow complet

### Scénario : Nouvel artiste approuvé

1. **Dashboard Central** : Tu approuves un artiste dans "Gestion Artistes"
2. **Dashboard** : Clone le template, déploie sur Render
3. **Template** : Au premier démarrage
   - Génère une API key unique
   - S'enregistre automatiquement sur le dashboard
   - Envoie : nom, URL, API key
4. **Dashboard** : Reçoit les infos, créé l'entrée dans la table `sites`
5. **Dashboard** : Affiche le nouveau site dans "Sites Gérés" avec :
   - Nom du site
   - URL cliquable
   - API key (masquée)
   - Status : Actif
   - Date d'enregistrement

---

## ✅ Avantages

- ✅ **Zéro configuration manuelle** : Tout est automatique
- ✅ **Pas d'interface API** dans le dashboard artiste : Invisible pour l'artiste
- ✅ **Centralisation** : Toutes les API keys sur un seul dashboard
- ✅ **Synchronisation** : Le dashboard connaît tous les sites déployés
- ✅ **Sécurisé** : Chaque site a sa propre API key unique

---

## 🔒 Sécurité

- L'API key est générée avec `secrets.token_urlsafe(32)` (256 bits)
- Stockée localement dans la table `settings`
- Jamais affichée dans l'interface admin du template
- Accessible uniquement via l'API ou le dashboard central

---

## 🐛 Debug

### Vérifier l'état d'enregistrement

Dans la console du serveur template au démarrage :

```
✅ Clé API générée automatiquement: a1b2c3d4e5...
✅ Site enregistré sur le dashboard central: Galerie Martin
```

Ou si erreur :
```
⚠️ Impossible de contacter le dashboard central: Connection timeout
```

### Logs côté Dashboard

```python
@app.route('/api/sites/register', methods=['POST'])
def register_site():
    data = request.get_json()
    print(f"📥 Nouveau site: {data.get('site_name')} - {data.get('site_url')}")
    # ... traitement ...
```

---

## 📝 Modifications apportées au Template

### Fichiers modifiés

1. **app.py**
   - Fonction `auto_generate_api_key()` : Génération automatique
   - Fonction `register_site_to_dashboard()` : Envoi au dashboard
   - Route `/api/sync-dashboard` : Re-synchronisation manuelle
   - Appel automatique au démarrage dans `if __name__ == "__main__"`

2. **templates/admin/admin_dashboard.html**
   - Suppression du lien "🔌 API Export"

3. **app.py (route commentée)**
   - Route `/admin/api-export` désactivée

---

## 🎨 Interface Dashboard Central (à implémenter)

### Page "Sites Gérés"

```
╔══════════════════════════════════════════════════════════╗
║  Sites Déployés                                          ║
╠══════════════════════════════════════════════════════════╣
║  📊 Total : 12 sites actifs                              ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  🎨 Galerie Martin                                       ║
║  🔗 https://galerie-martin.onrender.com                  ║
║  🔑 API: a1b2c3d4e5... [Copier] [Réinitialiser]        ║
║  📅 Enregistré : 01/12/2025 14:30                       ║
║  🟢 Actif                                                ║
║  ──────────────────────────────────────────────────      ║
║                                                          ║
║  🎨 Studio Léa Dubois                                    ║
║  🔗 https://studio-lea.onrender.com                      ║
║  🔑 API: z9y8x7w6v5... [Copier] [Réinitialiser]        ║
║  📅 Enregistré : 30/11/2025 10:15                       ║
║  🟢 Actif                                                ║
║  ──────────────────────────────────────────────────      ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

---

## 🔄 Mise à jour future

Si besoin de changer l'URL du dashboard central, modifier dans `app.py` :

```python
dashboard_url = "https://mydashboard-v39e.onrender.com/api/sites/register"
```
