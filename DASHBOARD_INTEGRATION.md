# Guide d'intégration Dashboard <-> Template

## Vue d'ensemble

Ce guide explique comment intégrer le Dashboard avec le Template pour synchroniser automatiquement les données.

---

## Architecture

```
┌─────────────────────┐
│   Dashboard         │
│   (Scalingo)        │
└──────────┬──────────┘
           │
           │ GET /api/export/* 
           │ Header: X-API-Key
           │
┌──────────▼──────────┐
│   Template          │
│   (Scalingo)        │
└─────────────────────┘
```

---

## 1. Configuration sur le Template

### Étape 1: Générer la clé API maître

```bash
# Générer une clé sécurisée
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Exemple de sortie:
# sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW
```

### Étape 2: Ajouter la clé au Template (Scalingo)

```bash
# Définir la variable d'environnement
scalingo -a template-production env-set \
  TEMPLATE_MASTER_API_KEY="sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW"

# Redémarrer l'app
scalingo -a template-production restart

# Vérifier qu'elle est définie
scalingo -a template-production env | grep TEMPLATE_MASTER_API_KEY
```

### Étape 3: Tester l'accès API

```bash
curl -H "X-API-Key: sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW" \
  https://example.artworksdigital.fr/api/export/settings | jq .
```

---

## 2. Configuration sur le Dashboard

### Étape 1: Ajouter la clé API

```bash
# Ajouter TEMPLATE_API_KEY avec la MÊME valeur que Template
scalingo -a dashboard-production env-set \
  TEMPLATE_API_KEY="sk_5pAcX8Yq-3KmL9xF_zBw2C7DqE4Rj5U6oN8pM1sVt9aW"

# Ajouter l'URL du Template
scalingo -a dashboard-production env-set \
  TEMPLATE_BASE_URL="https://example.artworksdigital.fr"

# Redémarrer
scalingo -a dashboard-production restart
```

### Étape 2: Créer un module de client API

**Fichier: `dashboard/clients/template_api.py`**

```python
import os
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TemplateAPIClient:
    """Client pour interagir avec l'API du Template"""
    
    def __init__(self):
        self.base_url = os.getenv('TEMPLATE_BASE_URL', '').rstrip('/')
        self.api_key = os.getenv('TEMPLATE_API_KEY')
        self.timeout = 30
        
        if not self.base_url:
            logger.warning("TEMPLATE_BASE_URL not configured")
        if not self.api_key:
            logger.warning("TEMPLATE_API_KEY not configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Construit les headers avec la clé API"""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, 
                params: Optional[Dict] = None, 
                json: Optional[Dict] = None) -> Dict[str, Any]:
        """Effectue une requête HTTP à l'API Template"""
        
        url = f"{self.base_url}/api/export/{endpoint}"
        
        try:
            logger.info(f"[TEMPLATE] {method} {endpoint}")
            
            if method == "GET":
                response = requests.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                    timeout=self.timeout
                )
            elif method == "PUT":
                response = requests.put(
                    url,
                    headers=self._get_headers(),
                    json=json,
                    timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            
            logger.info(f"[TEMPLATE] ✅ {response.status_code}")
            return response.json()
        
        except requests.exceptions.Timeout:
            logger.error(f"[TEMPLATE] Timeout: {endpoint}")
            raise Exception(f"Template API timeout: {endpoint}")
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"[TEMPLATE] HTTP {e.response.status_code}: {e.response.text}")
            if e.response.status_code == 401:
                raise Exception("Template API authentication failed - check TEMPLATE_API_KEY")
            raise
        
        except Exception as e:
            logger.error(f"[TEMPLATE] Error: {e}")
            raise
    
    def get_settings(self) -> Dict[str, str]:
        """Récupère tous les settings"""
        data = self._request("GET", "settings")
        settings = {}
        for item in data.get('data', []):
            settings[item['key']] = item['value']
        logger.info(f"[TEMPLATE] Got {len(settings)} settings")
        return settings
    
    def get_paintings(self, limit: int = 1000, offset: int = 0) -> list:
        """Récupère les peintures"""
        data = self._request("GET", "paintings", params={'limit': limit, 'offset': offset})
        logger.info(f"[TEMPLATE] Got {data.get('count', 0)} paintings")
        return data.get('data', [])
    
    def get_orders(self, limit: int = 100, offset: int = 0) -> list:
        """Récupère les commandes"""
        data = self._request("GET", "orders", params={'limit': limit, 'offset': offset})
        logger.info(f"[TEMPLATE] Got {data.get('count', 0)} orders")
        return data.get('data', [])
    
    def get_users(self) -> list:
        """Récupère les utilisateurs"""
        data = self._request("GET", "users")
        logger.info(f"[TEMPLATE] Got {data.get('count', 0)} users")
        return data.get('data', [])
    
    def get_exhibitions(self) -> list:
        """Récupère les expositions"""
        data = self._request("GET", "exhibitions")
        logger.info(f"[TEMPLATE] Got {data.get('count', 0)} exhibitions")
        return data.get('data', [])
    
    def get_custom_requests(self) -> list:
        """Récupère les demandes personnalisées"""
        data = self._request("GET", "custom-requests")
        logger.info(f"[TEMPLATE] Got {data.get('count', 0)} custom requests")
        return data.get('data', [])
    
    def get_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques"""
        data = self._request("GET", "stats")
        logger.info(f"[TEMPLATE] Got stats: {data.get('stats', {})}")
        return data.get('stats', {})
    
    def get_full_export(self) -> Dict[str, Any]:
        """Récupère TOUTES les données du Template"""
        data = self._request("GET", "full")
        logger.info(f"[TEMPLATE] Full export: {data.get('tables_count', 0)} tables, "
                   f"{data.get('total_records', 0)} records")
        return data.get('data', {})
    
    def health_check(self) -> bool:
        """Vérifie que l'API est accessible"""
        try:
            self.get_stats()
            logger.info("[TEMPLATE] Health check: ✅ OK")
            return True
        except Exception as e:
            logger.error(f"[TEMPLATE] Health check: ❌ {e}")
            return False


# Singleton instance
_client = None

def get_client() -> TemplateAPIClient:
    """Obtient l'instance du client (singleton)"""
    global _client
    if _client is None:
        _client = TemplateAPIClient()
    return _client
```

### Étape 3: Créer un service de synchronisation

**Fichier: `dashboard/services/sync_template.py`**

```python
import logging
from datetime import datetime
from dashboard.clients.template_api import get_client
from dashboard.models import (
    Setting, Painting, Order, OrderItem, User, Exhibition, CustomRequest
)
from dashboard.extensions import db

logger = logging.getLogger(__name__)

class TemplateSync:
    """Service pour synchroniser les données du Template"""
    
    @staticmethod
    def sync_settings() -> int:
        """Synchronise les settings du Template"""
        logger.info("[SYNC] Starting settings sync...")
        client = get_client()
        
        try:
            template_settings = client.get_settings()
            
            for key, value in template_settings.items():
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                    logger.debug(f"[SYNC] Updated setting: {key}")
                else:
                    setting = Setting(key=key, value=value)
                    db.session.add(setting)
                    logger.debug(f"[SYNC] Created setting: {key}")
            
            db.session.commit()
            count = len(template_settings)
            logger.info(f"[SYNC] ✅ Settings synced: {count} items")
            return count
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"[SYNC] ❌ Settings sync failed: {e}")
            raise
    
    @staticmethod
    def sync_paintings(limit: int = 1000) -> int:
        """Synchronise les peintures"""
        logger.info("[SYNC] Starting paintings sync...")
        client = get_client()
        
        try:
            paintings = client.get_paintings(limit=limit)
            
            for p in paintings:
                painting = Painting.query.filter_by(id=p['id']).first()
                if painting:
                    # Update existing
                    for key, value in p.items():
                        if hasattr(painting, key):
                            setattr(painting, key, value)
                    logger.debug(f"[SYNC] Updated painting: {p['name']}")
                else:
                    # Create new
                    painting = Painting(**p)
                    db.session.add(painting)
                    logger.debug(f"[SYNC] Created painting: {p['name']}")
            
            db.session.commit()
            logger.info(f"[SYNC] ✅ Paintings synced: {len(paintings)} items")
            return len(paintings)
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"[SYNC] ❌ Paintings sync failed: {e}")
            raise
    
    @staticmethod
    def sync_orders(limit: int = 100) -> int:
        """Synchronise les commandes"""
        logger.info("[SYNC] Starting orders sync...")
        client = get_client()
        
        try:
            orders = client.get_orders(limit=limit)
            
            for o in orders:
                order = Order.query.filter_by(id=o['id']).first()
                if not order:
                    # Les commandes ne sont jamais updatées, seulement crées
                    order = Order(**o)
                    db.session.add(order)
                    logger.debug(f"[SYNC] Created order: #{o['id']}")
            
            db.session.commit()
            logger.info(f"[SYNC] ✅ Orders synced: {len(orders)} items")
            return len(orders)
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"[SYNC] ❌ Orders sync failed: {e}")
            raise
    
    @staticmethod
    def sync_all() -> Dict[str, int]:
        """Synchronise TOUTES les données"""
        logger.info("[SYNC] ====== FULL SYNC START ======")
        start_time = datetime.now()
        
        results = {}
        
        try:
            results['settings'] = TemplateSync.sync_settings()
            results['paintings'] = TemplateSync.sync_paintings()
            results['orders'] = TemplateSync.sync_orders()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"[SYNC] ====== FULL SYNC COMPLETE ======")
            logger.info(f"[SYNC] Summary: {results}")
            logger.info(f"[SYNC] Time elapsed: {elapsed:.2f}s")
            
            return results
        
        except Exception as e:
            logger.error(f"[SYNC] ====== FULL SYNC FAILED ======")
            logger.error(f"[SYNC] Error: {e}")
            raise
```

### Étape 4: Ajouter un endpoint dans le Dashboard

**Fichier: `dashboard/routes/admin.py`**

```python
from flask import Blueprint, jsonify, request
from dashboard.services.sync_template import TemplateSync
from dashboard.clients.template_api import get_client
from dashboard.auth import require_admin
import logging

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)

@admin_bp.route('/api/sync-template', methods=['POST'])
@require_admin
def sync_template():
    """Déclenche une synchronisation avec le Template"""
    try:
        logger.info("[API] Sync request received")
        results = TemplateSync.sync_all()
        
        return jsonify({
            "success": True,
            "message": "Synchronization completed",
            "data": results
        })
    
    except Exception as e:
        logger.error(f"[API] Sync failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@admin_bp.route('/api/template-health', methods=['GET'])
@require_admin
def template_health():
    """Vérifie la santé de la connexion Template"""
    try:
        client = get_client()
        is_healthy = client.health_check()
        
        return jsonify({
            "success": True,
            "healthy": is_healthy,
            "base_url": client.base_url
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "healthy": False
        }), 500
```

### Étape 5: Ajouter un schedule (Celery)

**Fichier: `dashboard/celery_config.py`**

```python
from celery.schedules import crontab
from dashboard.services.sync_template import TemplateSync

# Configuration Celery Beat
app.conf.beat_schedule = {
    'sync-template-daily': {
        'task': 'dashboard.tasks.sync_template_task',
        'schedule': crontab(hour=2, minute=0),  # À 2h du matin
    },
    'template-health-check': {
        'task': 'dashboard.tasks.template_health_check',
        'schedule': crontab(minute=0),  # Toutes les heures
    }
}

# Fichier: dashboard/tasks.py
from celery import shared_task
from dashboard.services.sync_template import TemplateSync
import logging

logger = logging.getLogger(__name__)

@shared_task
def sync_template_task():
    """Tâche Celery pour synchroniser avec le Template"""
    try:
        logger.info("[CELERY] Starting Template sync task...")
        results = TemplateSync.sync_all()
        logger.info(f"[CELERY] Sync completed: {results}")
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"[CELERY] Sync failed: {e}")
        return {"success": False, "error": str(e)}

@shared_task
def template_health_check():
    """Tâche Celery pour vérifier la santé de l'API"""
    try:
        from dashboard.clients.template_api import get_client
        client = get_client()
        is_healthy = client.health_check()
        logger.info(f"[CELERY] Template health check: {'✅ OK' if is_healthy else '❌ FAILED'}")
        return {"healthy": is_healthy}
    except Exception as e:
        logger.error(f"[CELERY] Health check failed: {e}")
        return {"healthy": False, "error": str(e)}
```

---

## 3. Test de l'intégration

### Test manuel:

```python
# Dans une session Python ou script
from dashboard.clients.template_api import get_client
from dashboard.services.sync_template import TemplateSync

# Test 1: Vérifier la connexion
client = get_client()
if client.health_check():
    print("✅ API connection OK")
else:
    print("❌ API connection FAILED")

# Test 2: Récupérer les settings
settings = client.get_settings()
print(f"Settings: {len(settings)} items")

# Test 3: Synchroniser les données
results = TemplateSync.sync_all()
print(f"Sync results: {results}")
```

### Via curl:

```bash
# Health check
curl -H "Authorization: Bearer <token>" \
  https://dashboard.com/admin/api/template-health

# Déclencher une sync
curl -X POST \
  -H "Authorization: Bearer <token>" \
  https://dashboard.com/admin/api/sync-template
```

---

## 4. Vérifications

✅ **Checklist**:
- [ ] `TEMPLATE_MASTER_API_KEY` configuré sur Template
- [ ] `TEMPLATE_API_KEY` configuré sur Dashboard (même valeur)
- [ ] `TEMPLATE_BASE_URL` configuré sur Dashboard
- [ ] Client API peut faire une requête GET /api/export/settings
- [ ] Sync se déclenche via `/admin/api/sync-template`
- [ ] Sync fonctionne automatiquement à 2h du matin
- [ ] Logs montrent les syncs en cours
- [ ] Erreurs 401 gérées proprement

---

## 5. Monitoring

### Vérifier les logs:

```bash
# Dashboard
scalingo -a dashboard-production logs | tail -50 | grep -i "sync\|template"

# Template  
scalingo -a template-production logs | tail -50 | grep -i "api_key\|401"
```

### Métriques à tracker:
- Fréquence des syncs réussies/échouées
- Temps d'exécution des syncs
- Nombre d'items synchronisés
- Erreurs 401 (authentification)

