# 📋 Code à ajouter sur mydashboard-v39e.onrender.com

## 1. Modèle de base de données (models.py ou équivalent)

```python
from datetime import datetime
from your_db import db  # Importer ton ORM

class Site(db.Model):
    """Modèle pour stocker les sites template déployés"""
    __tablename__ = 'sites'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), unique=True, nullable=False)
    api_key = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.String(50), default='active')  # active, inactive, suspended
    auto_registered = db.Column(db.Boolean, default=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_sync = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relations
    artist = db.relationship('Artist', backref='sites')
    
    def __repr__(self):
        return f'<Site {self.name} - {self.url}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'api_key': self.api_key[:10] + '...',  # Masquer pour sécurité
            'status': self.status,
            'auto_registered': self.auto_registered,
            'artist_id': self.artist_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None
        }
```

---

## 2. Route d'enregistrement (routes.py ou app.py)

```python
from flask import request, jsonify
from datetime import datetime

@app.route('/api/sites/register', methods=['POST'])
def register_site():
    """
    Endpoint pour recevoir l'auto-registration des sites template
    
    Body JSON attendu:
    {
        "site_name": "Galerie Martin",
        "site_url": "https://galerie-martin.onrender.com",
        "api_key": "a1b2c3d4e5f6...",
        "auto_registered": true
    }
    """
    try:
        data = request.get_json()
        
        # Validation des données
        site_name = data.get('site_name')
        site_url = data.get('site_url')
        api_key = data.get('api_key')
        auto_registered = data.get('auto_registered', False)
        
        if not all([site_name, site_url, api_key]):
            return jsonify({
                'success': False,
                'error': 'Données manquantes (site_name, site_url, api_key requis)'
            }), 400
        
        # Nettoyer l'URL (retirer trailing slash)
        site_url = site_url.rstrip('/')
        
        # Vérifier si le site existe déjà (par URL)
        existing_site = Site.query.filter_by(url=site_url).first()
        
        if existing_site:
            # Mettre à jour l'API key et la date de sync
            existing_site.api_key = api_key
            existing_site.name = site_name  # Mettre à jour le nom aussi
            existing_site.last_sync = datetime.utcnow()
            existing_site.status = 'active'
            
            db.session.commit()
            
            print(f"✅ Site mis à jour: {site_name} ({site_url})")
            
            return jsonify({
                'success': True,
                'site_id': existing_site.id,
                'message': 'Site mis à jour avec succès',
                'updated': True
            }), 200
        
        # Créer un nouveau site
        new_site = Site(
            name=site_name,
            url=site_url,
            api_key=api_key,
            status='active',
            auto_registered=auto_registered,
            created_at=datetime.utcnow(),
            last_sync=datetime.utcnow()
        )
        
        db.session.add(new_site)
        db.session.commit()
        
        print(f"🆕 Nouveau site enregistré: {site_name} ({site_url})")
        
        return jsonify({
            'success': True,
            'site_id': new_site.id,
            'message': 'Site enregistré avec succès',
            'updated': False
        }), 200
    
    except Exception as e:
        print(f"❌ Erreur lors de l'enregistrement: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sites/<int:site_id>', methods=['GET'])
def get_site(site_id):
    """Récupérer les infos d'un site spécifique"""
    site = Site.query.get_or_404(site_id)
    return jsonify({
        'success': True,
        'site': site.to_dict()
    })


@app.route('/api/sites', methods=['GET'])
def list_sites():
    """Lister tous les sites enregistrés"""
    sites = Site.query.order_by(Site.created_at.desc()).all()
    return jsonify({
        'success': True,
        'count': len(sites),
        'sites': [site.to_dict() for site in sites]
    })


@app.route('/api/sites/<int:site_id>/regenerate-key', methods=['POST'])
def regenerate_site_key(site_id):
    """Régénérer l'API key d'un site"""
    import secrets
    
    site = Site.query.get_or_404(site_id)
    
    # Générer une nouvelle clé
    new_api_key = secrets.token_urlsafe(32)
    site.api_key = new_api_key
    site.last_sync = datetime.utcnow()
    
    db.session.commit()
    
    # TODO: Envoyer la nouvelle clé au site via webhook
    # requests.post(f"{site.url}/api/update-key", json={'api_key': new_api_key})
    
    return jsonify({
        'success': True,
        'message': 'Clé API régénérée',
        'new_key': new_api_key
    })


@app.route('/api/sites/<int:site_id>', methods=['DELETE'])
def delete_site(site_id):
    """Supprimer un site"""
    site = Site.query.get_or_404(site_id)
    
    db.session.delete(site)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Site {site.name} supprimé'
    })
```

---

## 3. Page de gestion des sites (template HTML)

```html
{% extends "base.html" %}

{% block content %}
<div class="container">
    <h1>🌐 Sites Déployés</h1>
    
    <div class="stats-card">
        <p>Total: <strong>{{ sites|length }}</strong> sites actifs</p>
    </div>
    
    <div class="sites-grid">
        {% for site in sites %}
        <div class="site-card">
            <div class="site-header">
                <h3>🎨 {{ site.name }}</h3>
                <span class="badge badge-{{ site.status }}">{{ site.status }}</span>
            </div>
            
            <div class="site-info">
                <p><strong>🔗 URL:</strong> 
                    <a href="{{ site.url }}" target="_blank">{{ site.url }}</a>
                </p>
                
                <p><strong>🔑 API Key:</strong> 
                    <code id="api-{{ site.id }}">{{ site.api_key[:10] }}...</code>
                    <button onclick="copyApiKey('{{ site.api_key }}', '{{ site.id }}')">
                        📋 Copier
                    </button>
                </p>
                
                <p><strong>📅 Enregistré:</strong> 
                    {{ site.created_at.strftime('%d/%m/%Y %H:%M') }}
                </p>
                
                <p><strong>🔄 Dernière sync:</strong> 
                    {{ site.last_sync.strftime('%d/%m/%Y %H:%M') }}
                </p>
                
                {% if site.artist %}
                <p><strong>👤 Artiste:</strong> 
                    <a href="{{ url_for('artist_detail', id=site.artist_id) }}">
                        {{ site.artist.name }}
                    </a>
                </p>
                {% endif %}
            </div>
            
            <div class="site-actions">
                <button onclick="regenerateKey({{ site.id }})" class="btn-warning">
                    🔄 Régénérer API
                </button>
                <button onclick="deleteSite({{ site.id }})" class="btn-danger">
                    🗑️ Supprimer
                </button>
            </div>
        </div>
        {% endfor %}
    </div>
</div>

<script>
function copyApiKey(key, siteId) {
    navigator.clipboard.writeText(key);
    alert('Clé API copiée !');
}

function regenerateKey(siteId) {
    if (!confirm('Régénérer la clé API ? L\'ancienne ne fonctionnera plus.')) return;
    
    fetch(`/api/sites/${siteId}/regenerate-key`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('Clé régénérée : ' + data.new_key);
            location.reload();
        }
    });
}

function deleteSite(siteId) {
    if (!confirm('Supprimer ce site définitivement ?')) return;
    
    fetch(`/api/sites/${siteId}`, {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'}
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('Site supprimé');
            location.reload();
        }
    });
}
</script>

<style>
.sites-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 20px;
    margin-top: 20px;
}

.site-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.site-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.site-info p {
    margin: 10px 0;
    font-size: 14px;
}

.site-info code {
    background: #f0f0f0;
    padding: 4px 8px;
    border-radius: 4px;
    font-family: monospace;
}

.site-actions {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}

.badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}

.badge-active { background: #10b981; color: white; }
.badge-inactive { background: #6b7280; color: white; }
</style>
{% endblock %}
```

---

## 4. Route pour afficher la page

```python
@app.route('/admin/sites')
@require_admin  # Ton décorateur d'authentification
def admin_sites():
    """Page de gestion des sites"""
    sites = Site.query.order_by(Site.created_at.desc()).all()
    return render_template('admin/sites.html', sites=sites)
```

---

## 5. Migration SQL (si besoin)

```sql
-- Créer la table sites
CREATE TABLE sites (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) UNIQUE NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    auto_registered BOOLEAN DEFAULT FALSE,
    artist_id INTEGER REFERENCES artists(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour performance
CREATE INDEX idx_sites_url ON sites(url);
CREATE INDEX idx_sites_artist_id ON sites(artist_id);
CREATE INDEX idx_sites_status ON sites(status);
```

---

## 6. Test manuel

```bash
# Tester l'endpoint d'enregistrement
curl -X POST https://mydashboard-v39e.onrender.com/api/sites/register \
  -H "Content-Type: application/json" \
  -d '{
    "site_name": "Test Gallery",
    "site_url": "https://test-gallery.onrender.com",
    "api_key": "test_api_key_123456789",
    "auto_registered": true
  }'

# Réponse attendue:
{
  "success": true,
  "site_id": 1,
  "message": "Site enregistré avec succès",
  "updated": false
}
```

---

## 7. Intégration avec le workflow artiste

Quand tu acceptes un artiste :

```python
@app.route('/admin/artists/<int:artist_id>/approve', methods=['POST'])
def approve_artist(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    
    # 1. Marquer comme approuvé
    artist.status = 'approved'
    db.session.commit()
    
    # 2. Cloner et déployer le template (via Render API ou GitHub Actions)
    site_url = deploy_template_for_artist(artist)
    
    # 3. Le site s'enregistrera automatiquement au démarrage
    # Pas besoin de code ici, c'est automatique !
    
    # 4. Optionnel: Lier le site à l'artiste après quelques secondes
    # (attendre que le site se soit auto-enregistré)
    
    flash(f'Artiste approuvé ! Le site sera disponible à {site_url}')
    return redirect(url_for('admin_artists'))
```

---

## 8. Vérifications de sécurité

```python
# Dans config.py ou settings
ALLOWED_TEMPLATE_DOMAINS = [
    'onrender.com',
    'herokuapp.com',
    'vercel.app',
    # Ajouter les domaines autorisés
]

# Dans la route register_site
from urllib.parse import urlparse

def is_allowed_domain(url):
    domain = urlparse(url).netloc
    return any(allowed in domain for allowed in ALLOWED_TEMPLATE_DOMAINS)

# Vérifier avant d'enregistrer
if not is_allowed_domain(site_url):
    return jsonify({
        'success': False,
        'error': 'Domaine non autorisé'
    }), 403
```
