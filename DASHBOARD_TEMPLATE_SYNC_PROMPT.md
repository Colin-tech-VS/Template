# Prompt Zencodeur: Dashboard - Réception des données Template

## Objectif

Implémenter un système complet de synchronisation des données du Template vers le Dashboard. Le Dashboard doit pouvoir:

1. Récupérer toutes les données du Template via les endpoints d'export
2. Valider la structure JSON de chaque réponse
3. Mettre à jour l'interface du Dashboard avec les données synchronisées
4. Gérer les erreurs et les cas de déconnexion
5. Afficher les statuts de synchronisation en temps réel

---

## Architecture

### Flux de données

```
Template (Artiste)                    Dashboard (Admin)
─────────────────                     ─────────────────
  GET /api/export/paintings  ────→   Reçoit peintures
         (+ X-API-Key)               ↓
                                   Valide JSON
                                     ↓
                                  Stocke en BD
                                     ↓
                                  Met à jour UI

  GET /api/export/users      ────→   Reçoit utilisateurs
  GET /api/export/orders     ────→   Reçoit commandes
  GET /api/export/settings   ────→   Reçoit paramètres
  GET /api/export/exhibitions ───→   Reçoit expositions
  GET /api/export/stats      ────→   Reçoit statistiques
```

---

## 1. Définir les modèles de réception

### 1.1 Modèle Painting

```python
# models/painting.py ou similar
class TemplatePainting:
    """Données reçues du Template pour une peinture"""
    
    id: int
    name: str
    price: float
    category: str
    technique: str
    year: int
    quantity: int
    status: str  # "Disponible", "Vendu", etc.
    image: str  # "Images/painting_123.jpg"
    display_order: int
    site_name: str  # Nom du site Template
    
    # Métadonnées
    template_url: str  # Pour tracker la provenance
    sync_timestamp: datetime
    
    @classmethod
    def from_template_api(cls, data: dict, site_url: str):
        """Parse les données reçues du Template"""
        return cls(
            id=data['id'],
            name=data['name'],
            price=float(data['price']),
            category=data['category'],
            technique=data.get('technique', ''),
            year=int(data.get('year', 0)),
            quantity=int(data.get('quantity', 1)),
            status=data.get('status', 'Disponible'),
            image=data.get('image', ''),
            display_order=int(data.get('display_order', 0)),
            site_name=data.get('site_name', 'Site Artiste'),
            template_url=site_url,
            sync_timestamp=datetime.now()
        )
```

### 1.2 Modèle User

```python
class TemplateUser:
    """Données reçues du Template pour un utilisateur"""
    
    id: int
    name: str
    email: str
    create_date: str
    role: str  # "admin" ou "user"
    site_name: str
    template_url: str
    sync_timestamp: datetime
    
    @classmethod
    def from_template_api(cls, data: dict, site_url: str):
        return cls(
            id=data['id'],
            name=data['name'],
            email=data['email'],
            create_date=data['create_date'],
            role=data.get('role', 'user'),  # default "user"
            site_name=data.get('site_name', ''),
            template_url=site_url,
            sync_timestamp=datetime.now()
        )
```

### 1.3 Modèle Order

```python
class TemplateOrder:
    """Données reçues du Template pour une commande"""
    
    id: int
    customer_name: str
    email: str
    total_price: float
    order_date: str
    status: str
    items: list  # [{painting_id, name, image, price, quantity}, ...]
    site_name: str
    template_url: str
    sync_timestamp: datetime
    
    @classmethod
    def from_template_api(cls, data: dict, site_url: str):
        return cls(
            id=data['id'],
            customer_name=data['customer_name'],
            email=data['email'],
            total_price=float(data['total_price']),
            order_date=data['order_date'],
            status=data['status'],
            items=data.get('items', []),
            site_name=data.get('site_name', ''),
            template_url=site_url,
            sync_timestamp=datetime.now()
        )
```

### 1.4 Modèle Settings

```python
class TemplateSettings:
    """Paramètres reçus du Template"""
    
    data: dict  # {key: value, ...}
    template_url: str
    sync_timestamp: datetime
    
    # Clés importantes
    @property
    def site_name(self):
        return next((s['value'] for s in self.data if s['key'] == 'site_name'), None)
    
    @property
    def site_logo(self):
        return next((s['value'] for s in self.data if s['key'] == 'site_logo'), None)
    
    @property
    def stripe_publishable_key(self):
        return next((s['value'] for s in self.data if s['key'] == 'stripe_publishable_key'), None)
    
    @property
    def saas_site_price_cache(self):
        val = next((s['value'] for s in self.data if s['key'] == 'saas_site_price_cache'), None)
        return float(val) if val else None
```

---

## 2. Créer le client multi-site

### 2.1 TemplateClient

```python
# clients/template_client.py

import requests
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class TemplateClient:
    """Client pour communiquer avec un Template"""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Args:
            base_url: URL du Template (ex: https://template.artworksdigital.fr)
            api_key: Clé API du Template (X-API-Key header)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = 10
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Requête générique avec gestion d'erreur"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'ArtworksdigitalDashboard/1.0'
        }
        
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            logger.error(f"Connexion refusée: {url}")
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Timeout: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                logger.error(f"API key invalide pour {self.base_url}")
            elif response.status_code == 404:
                logger.warning(f"Endpoint non trouvé: {endpoint}")
            else:
                logger.error(f"Erreur HTTP {response.status_code}: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Erreur parsing JSON: {e}")
            return None
    
    def get_paintings(self, limit=200, offset=0) -> Optional[List[Dict]]:
        """Récupère les peintures du Template"""
        data = self._request(
            'GET',
            '/api/export/paintings',
            params={'limit': limit, 'offset': offset}
        )
        if data and data.get('paintings'):
            return data['paintings']
        return None
    
    def get_users(self, limit=500, offset=0) -> Optional[List[Dict]]:
        """Récupère les utilisateurs du Template"""
        data = self._request(
            'GET',
            '/api/export/users',
            params={'limit': limit, 'offset': offset}
        )
        if data and data.get('users'):
            return data['users']
        return None
    
    def get_orders(self, limit=100, offset=0) -> Optional[List[Dict]]:
        """Récupère les commandes du Template"""
        data = self._request(
            'GET',
            '/api/export/orders',
            params={'limit': limit, 'offset': offset}
        )
        if data and data.get('orders'):
            return data['orders']
        return None
    
    def get_settings(self) -> Optional[List[Dict]]:
        """Récupère les paramètres du Template"""
        data = self._request('GET', '/api/export/settings')
        if data and data.get('data'):
            return data['data']
        return None
    
    def get_exhibitions(self) -> Optional[List[Dict]]:
        """Récupère les expositions du Template"""
        data = self._request('GET', '/api/export/exhibitions')
        if data and data.get('exhibitions'):
            return data['exhibitions']
        return None
    
    def get_stats(self) -> Optional[Dict]:
        """Récupère les statistiques du Template"""
        data = self._request('GET', '/api/export/stats')
        if data and data.get('stats'):
            return data['stats']
        return None
```

---

## 3. Créer le synchroniseur

### 3.1 TemplateSynchronizer

```python
# services/template_synchronizer.py

import logging
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class TemplateSynchronizer:
    """Synchronise les données du Template vers le Dashboard"""
    
    def __init__(self, db, template_client):
        self.db = db
        self.client = template_client
        self.sync_log = []
    
    def sync_all(self) -> Dict:
        """Synchronise TOUTES les données du Template"""
        results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'paintings': self.sync_paintings(),
            'users': self.sync_users(),
            'orders': self.sync_orders(),
            'settings': self.sync_settings(),
            'exhibitions': self.sync_exhibitions(),
            'stats': self.sync_stats(),
            'log': self.sync_log
        }
        
        # Calculer le statut global
        results['success'] = all([
            results['paintings']['success'],
            results['users']['success'],
            results['orders']['success'],
            results['settings']['success']
        ])
        
        return results
    
    def sync_paintings(self) -> Dict:
        """Synchronise les peintures"""
        try:
            paintings = self.client.get_paintings()
            if not paintings:
                self._log("paintings", "ERROR", "Aucune donnée reçue")
                return {'success': False, 'count': 0}
            
            # Valider chaque peinture
            valid_count = 0
            for painting in paintings:
                if self._validate_painting(painting):
                    self._upsert_painting(painting)
                    valid_count += 1
                else:
                    self._log("paintings", "WARNING", f"Peinture invalide: {painting.get('id')}")
            
            self._log("paintings", "SUCCESS", f"{valid_count}/{len(paintings)} peintures synchronisées")
            return {'success': True, 'count': valid_count}
        except Exception as e:
            self._log("paintings", "ERROR", str(e))
            return {'success': False, 'count': 0}
    
    def sync_users(self) -> Dict:
        """Synchronise les utilisateurs"""
        try:
            users = self.client.get_users()
            if not users:
                self._log("users", "ERROR", "Aucune donnée reçue")
                return {'success': False, 'count': 0}
            
            valid_count = 0
            for user in users:
                if self._validate_user(user):
                    self._upsert_user(user)
                    valid_count += 1
            
            self._log("users", "SUCCESS", f"{valid_count}/{len(users)} utilisateurs synchronisés")
            return {'success': True, 'count': valid_count}
        except Exception as e:
            self._log("users", "ERROR", str(e))
            return {'success': False, 'count': 0}
    
    def sync_orders(self) -> Dict:
        """Synchronise les commandes"""
        try:
            orders = self.client.get_orders()
            if not orders:
                self._log("orders", "ERROR", "Aucune donnée reçue")
                return {'success': False, 'count': 0}
            
            valid_count = 0
            for order in orders:
                if self._validate_order(order):
                    self._upsert_order(order)
                    valid_count += 1
            
            self._log("orders", "SUCCESS", f"{valid_count}/{len(orders)} commandes synchronisées")
            return {'success': True, 'count': valid_count}
        except Exception as e:
            self._log("orders", "ERROR", str(e))
            return {'success': False, 'count': 0}
    
    def sync_settings(self) -> Dict:
        """Synchronise les paramètres"""
        try:
            settings = self.client.get_settings()
            if not settings:
                self._log("settings", "ERROR", "Aucune donnée reçue")
                return {'success': False, 'count': 0}
            
            self._upsert_settings(settings)
            self._log("settings", "SUCCESS", f"{len(settings)} paramètres synchronisés")
            return {'success': True, 'count': len(settings)}
        except Exception as e:
            self._log("settings", "ERROR", str(e))
            return {'success': False, 'count': 0}
    
    def sync_exhibitions(self) -> Dict:
        """Synchronise les expositions"""
        try:
            exhibitions = self.client.get_exhibitions()
            if not exhibitions:
                return {'success': True, 'count': 0}
            
            for exhibition in exhibitions:
                self._upsert_exhibition(exhibition)
            
            return {'success': True, 'count': len(exhibitions)}
        except Exception as e:
            self._log("exhibitions", "ERROR", str(e))
            return {'success': False, 'count': 0}
    
    def sync_stats(self) -> Dict:
        """Synchronise les statistiques"""
        try:
            stats = self.client.get_stats()
            if not stats:
                return {'success': True, 'data': {}}
            
            self._cache_stats(stats)
            return {'success': True, 'data': stats}
        except Exception as e:
            return {'success': False, 'data': {}}
    
    # ===== VALIDATIONS =====
    
    def _validate_painting(self, painting: Dict) -> bool:
        """Valide une peinture"""
        required = ['id', 'name', 'price', 'category', 'image']
        return all(key in painting and painting[key] for key in required)
    
    def _validate_user(self, user: Dict) -> bool:
        """Valide un utilisateur"""
        required = ['id', 'name', 'email']
        return all(key in user and user[key] for key in required)
    
    def _validate_order(self, order: Dict) -> bool:
        """Valide une commande"""
        required = ['id', 'customer_name', 'email', 'total_price', 'order_date']
        return all(key in order and order[key] for key in required)
    
    # ===== UPSERTS (Update or Insert) =====
    
    def _upsert_painting(self, painting: Dict):
        """Insère ou met à jour une peinture"""
        # À adapter selon votre schéma Dashboard
        query = """
            INSERT INTO template_paintings (
                template_id, name, price, category, technique, year,
                quantity, status, image, display_order, site_name, sync_timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (template_id) DO UPDATE SET
                name=EXCLUDED.name,
                price=EXCLUDED.price,
                ... (autres colonnes)
        """
        self.db.execute(query, (
            painting['id'],
            painting['name'],
            painting['price'],
            painting['category'],
            painting.get('technique', ''),
            painting.get('year', 0),
            painting.get('quantity', 1),
            painting.get('status', 'Disponible'),
            painting.get('image', ''),
            painting.get('display_order', 0),
            painting.get('site_name', ''),
            datetime.now()
        ))
    
    def _upsert_user(self, user: Dict):
        """Insère ou met à jour un utilisateur"""
        query = """
            INSERT INTO template_users (
                template_user_id, name, email, role, create_date, site_name, sync_timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (template_user_id) DO UPDATE SET
                name=EXCLUDED.name,
                role=EXCLUDED.role,
                sync_timestamp=EXCLUDED.sync_timestamp
        """
        self.db.execute(query, (
            user['id'],
            user['name'],
            user['email'],
            user.get('role', 'user'),
            user['create_date'],
            user.get('site_name', ''),
            datetime.now()
        ))
    
    def _upsert_order(self, order: Dict):
        """Insère ou met à jour une commande"""
        # Implémenter selon votre schéma
        pass
    
    def _upsert_settings(self, settings: List[Dict]):
        """Insère ou met à jour les paramètres"""
        for setting in settings:
            # Éviter de stocker les clés sensibles masquées
            if setting['value'] == '***MASKED***':
                continue
            
            query = """
                INSERT INTO template_settings (key, value, sync_timestamp)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE SET
                    value=EXCLUDED.value,
                    sync_timestamp=EXCLUDED.sync_timestamp
            """
            self.db.execute(query, (
                setting['key'],
                setting['value'],
                datetime.now()
            ))
    
    def _upsert_exhibition(self, exhibition: Dict):
        """Insère ou met à jour une exposition"""
        pass
    
    def _cache_stats(self, stats: Dict):
        """Cache les statistiques"""
        query = """
            INSERT INTO template_stats (data, sync_timestamp)
            VALUES (%s, %s)
        """
        self.db.execute(query, (
            json.dumps(stats),
            datetime.now()
        ))
    
    # ===== LOGGING =====
    
    def _log(self, entity: str, level: str, message: str):
        """Log un événement de synchronisation"""
        log_entry = {
            'entity': entity,
            'level': level,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.sync_log.append(log_entry)
        
        if level == 'ERROR':
            logger.error(f"[{entity}] {message}")
        elif level == 'WARNING':
            logger.warning(f"[{entity}] {message}")
        else:
            logger.info(f"[{entity}] {message}")
```

---

## 4. Créer les routes API Dashboard

### 4.1 Route de synchronisation manuelle

```python
# dashboard/routes/sync.py

from flask import Blueprint, jsonify, request
from services.template_synchronizer import TemplateSynchronizer
from clients.template_client import TemplateClient
from decorators import require_admin

bp = Blueprint('sync', __name__, url_prefix='/api/sync')

@bp.route('/template/<site_id>', methods=['POST'])
@require_admin
def sync_template(site_id):
    """
    Synchronise manuellement les données d'un Template
    
    POST /api/sync/template/{site_id}
    """
    try:
        # Récupérer la configuration du site
        site = get_site(site_id)
        if not site:
            return jsonify({'success': False, 'error': 'Site not found'}), 404
        
        # Créer le client Template
        template_url = site['template_url']
        api_key = site['template_api_key']
        client = TemplateClient(template_url, api_key)
        
        # Synchroniser
        synchronizer = TemplateSynchronizer(db, client)
        results = synchronizer.sync_all()
        
        return jsonify({
            'success': results['success'],
            'timestamp': results['timestamp'],
            'summary': {
                'paintings': results['paintings'],
                'users': results['users'],
                'orders': results['orders'],
                'settings': results['settings'],
                'exhibitions': results['exhibitions']
            },
            'log': results['log']
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

### 4.2 Route de webhook (optionnel)

```python
@bp.route('/webhook/template', methods=['POST'])
def webhook_template():
    """
    Reçoit les notifications du Template quand des données changent
    Template can POST to: https://dashboard.artworksdigital.fr/api/sync/webhook/template
    """
    try:
        data = request.get_json()
        event = data.get('event')  # painting_updated, order_created, etc.
        site_id = data.get('site_id')
        
        if event == 'painting_updated':
            # Synchroniser juste les peintures
            ...
        elif event == 'order_created':
            # Synchroniser les commandes
            ...
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False}), 500
```

---

## 5. Mise à jour de l'UI Dashboard

### 5.1 Affichage des peintures

```html
<!-- dashboard/templates/paintings.html -->

<div class="paintings-container">
    {% for painting in paintings %}
    <div class="painting-card">
        <img src="{{ painting.image_url }}" alt="{{ painting.name }}">
        <h3>{{ painting.name }}</h3>
        <p class="category">{{ painting.category }}</p>
        <p class="price">{{ painting.price }} €</p>
        <p class="status">
            <span class="status-badge" data-status="{{ painting.status }}">
                {{ painting.status }}
            </span>
        </p>
        <p class="site">De: <strong>{{ painting.site_name }}</strong></p>
        <p class="sync-date">Synchronisé: {{ painting.sync_timestamp }}</p>
    </div>
    {% endfor %}
</div>
```

### 5.2 Affichage des utilisateurs avec rôles

```html
<!-- dashboard/templates/users.html -->

<table class="users-table">
    <thead>
        <tr>
            <th>Nom</th>
            <th>Email</th>
            <th>Rôle</th>
            <th>Date d'inscription</th>
            <th>Site</th>
        </tr>
    </thead>
    <tbody>
        {% for user in users %}
        <tr>
            <td>{{ user.name }}</td>
            <td>{{ user.email }}</td>
            <td>
                <span class="role-badge" data-role="{{ user.role }}">
                    {% if user.role == 'admin' %}
                        👤 Administrateur
                    {% else %}
                        👥 Utilisateur
                    {% endif %}
                </span>
            </td>
            <td>{{ user.create_date }}</td>
            <td>{{ user.site_name }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

### 5.3 Affichage des commandes

```html
<!-- dashboard/templates/orders.html -->

<div class="orders-list">
    {% for order in orders %}
    <div class="order-card">
        <h3>Commande #{order.id}</h3>
        <p><strong>Client:</strong> {{ order.customer_name }}</p>
        <p><strong>Email:</strong> {{ order.email }}</p>
        <p><strong>Total:</strong> {{ order.total_price }} €</p>
        <p><strong>Date:</strong> {{ order.order_date }}</p>
        <p><strong>Statut:</strong> {{ order.status }}</p>
        
        <h4>Articles:</h4>
        <ul>
        {% for item in order.items %}
            <li>{{ item.name }} - {{ item.price }} € (x{{ item.quantity }})</li>
        {% endfor %}
        </ul>
    </div>
    {% endfor %}
</div>
```

---

## 6. Gestion des erreurs

```python
# services/template_error_handler.py

class TemplateError(Exception):
    """Erreur générique Template"""
    pass

class TemplateConnectionError(TemplateError):
    """Connexion impossible"""
    pass

class TemplateAuthenticationError(TemplateError):
    """Authentification échouée (clé API invalide)"""
    pass

class TemplateValidationError(TemplateError):
    """Données invalides reçues"""
    pass

# Dans le synchronizer
def sync_all(self) -> Dict:
    try:
        ...
    except TemplateConnectionError:
        self._log("sync", "ERROR", "Connection timeout - Template indisponible")
    except TemplateAuthenticationError:
        self._log("sync", "ERROR", "API key invalide")
    except TemplateValidationError:
        self._log("sync", "ERROR", "Données invalides reçues")
```

---

## 7. Tests manuels (voir section suivante)

---

## 📋 Checklist d'implémentation

- [ ] Modèles créés (Painting, User, Order, Settings)
- [ ] TemplateClient implémenté (requêtes HTTP)
- [ ] TemplateSynchronizer implémenté (logique sync)
- [ ] Routes API Dashboard créées
- [ ] Base de données préparée (tables template_*)
- [ ] UI mise à jour (affichage peintures, utilisateurs, commandes)
- [ ] Gestion des erreurs complète
- [ ] Tests manuels passés
- [ ] Validation JSON dans chaque endpoint
- [ ] Logging complet des synchronisations

---

## 🚀 Prochaines étapes

1. Implémenter le TemplateSynchronizer
2. Créer les routes API Dashboard
3. Mettre à jour l'UI
4. Tester la synchronisation complète
5. Mettre en place le webhook (optionnel mais recommandé)

