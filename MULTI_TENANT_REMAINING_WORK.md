# Multi-Tenant Isolation - Remaining Work

## Résumé

Ce document liste TOUTES les requêtes restantes à modifier pour garantir l'isolation stricte par tenant_id.

## Statut Global

- ✅ **TERMINÉ**: Tables mises à jour avec tenant_id (14 tables)
- ✅ **TERMINÉ**: Script de migration créé
- ✅ **TERMINÉ**: Routes critiques mises à jour (peintures, utilisateurs, favoris, admin, API export)
- ⚠️  **EN COURS**: ~90 requêtes restantes à mettre à jour

## Pattern de Modification

Pour chaque route/fonction:

```python
# 1. Récupérer tenant_id au début de la fonction
tenant_id = get_current_tenant_id()

# 2. SELECT: Ajouter tenant_id au WHERE
c.execute(adapt_query("SELECT ... FROM table WHERE ... AND tenant_id=?"), (..., tenant_id))

# 3. INSERT: Ajouter tenant_id aux colonnes et valeurs
c.execute(adapt_query("INSERT INTO table (..., tenant_id) VALUES (..., ?)"), (..., tenant_id))

# 4. UPDATE: Ajouter tenant_id au WHERE
c.execute(adapt_query("UPDATE table SET ... WHERE id=? AND tenant_id=?"), (..., id, tenant_id))

# 5. DELETE: Ajouter tenant_id au WHERE
c.execute(adapt_query("DELETE FROM table WHERE id=? AND tenant_id=?"), (id, tenant_id))

# 6. JOIN: Filtrer toutes les tables par tenant_id
SELECT ... FROM t1 
JOIN t2 ON t1.x = t2.x AND t1.tenant_id = t2.tenant_id 
WHERE t1.tenant_id=?
```

## Requêtes par Catégorie

### 1. ORDERS & ORDER_ITEMS (~15 requêtes restantes)

#### Fichier: app.py

**Fonction: `checkout()` (ligne ~1960-2100)**
- [ ] SELECT cart_id WHERE user_id → ajouter tenant_id
- [ ] SELECT cart_items JOIN paintings → ajouter tenant_id aux deux tables
- [ ] INSERT INTO orders → ajouter tenant_id
- [ ] INSERT INTO order_items → ajouter tenant_id (+ valider que painting_id est dans même tenant)
- [ ] UPDATE paintings SET quantity → ajouter tenant_id
- [ ] DELETE FROM cart_items → ajouter tenant_id
- [ ] DELETE FROM carts → ajouter tenant_id

**Fonction: `checkout_success()` (ligne ~2280-2337)**
- ✅ Déjà fait

**Fonction: `admin_order_detail()` (ligne ~3750)**
- [ ] SELECT FROM orders WHERE id → ajouter tenant_id
- [ ] SELECT FROM order_items WHERE order_id → ajouter tenant_id

**Fonction: `admin_update_order_status()` (ligne ~3800)**
- [ ] UPDATE orders WHERE id → ajouter tenant_id

**Fonction: API `/api/export/stats` (ligne ~4520)**
- [ ] SELECT SUM FROM orders → ajouter tenant_id
- [ ] SELECT COUNT FROM orders WHERE status → ajouter tenant_id

### 2. CART & CART_ITEMS (~15 requêtes)

#### Fichier: app.py

**Fonction: `inject_cart()` (ligne ~2644-2720)**
- [ ] SELECT carts WHERE user_id → ajouter tenant_id
- [ ] SELECT carts WHERE session_id → ajouter tenant_id
- [ ] SELECT cart_items JOIN paintings → ajouter tenant_id aux deux
- [ ] SELECT favorites WHERE user_id → ajouter tenant_id

**Fonction: `panier()` (ligne ~2000-2100)**
- [ ] SELECT carts → ajouter tenant_id
- [ ] SELECT cart_items JOIN paintings → ajouter tenant_id

**Fonction: `add_to_cart()` (ligne ~1800-1900)**
- [ ] SELECT carts → ajouter tenant_id
- [ ] INSERT INTO carts → ajouter tenant_id
- [ ] SELECT cart_items → ajouter tenant_id
- [ ] INSERT INTO cart_items → ajouter tenant_id (+ valider painting_id)
- [ ] UPDATE cart_items → ajouter tenant_id

**Fonction: `remove_from_cart()` (ligne ~2100-2150)**
- [ ] DELETE FROM cart_items WHERE cart_id AND painting_id → ajouter tenant_id

**Fonction: `merge_carts()` (ligne ~1100-1180)**
- [ ] SELECT carts WHERE user_id → ajouter tenant_id
- [ ] SELECT cart_items WHERE cart_id → ajouter tenant_id (les 2 fois)
- [ ] INSERT INTO carts → ajouter tenant_id
- [ ] UPDATE/INSERT cart_items → ajouter tenant_id
- [ ] DELETE cart_items → ajouter tenant_id
- [ ] DELETE carts → ajouter tenant_id
- [ ] UPDATE carts → ajouter tenant_id

### 3. PAINTINGS ADMIN (~20 requêtes)

#### Fichier: app.py

**Fonction: `admin_paintings()` (ligne ~2850)**
- [ ] SELECT FROM paintings → ajouter tenant_id

**Fonction: `admin_painting_detail()` (ligne ~2900)**
- [ ] SELECT FROM paintings WHERE id → ajouter tenant_id

**Fonction: `edit_painting()` (ligne ~3500)**
- [ ] SELECT FROM paintings WHERE id → ajouter tenant_id
- [ ] UPDATE paintings WHERE id → ajouter tenant_id

**Fonction: `delete_painting()` (ligne ~3470-3490)**
- [ ] SELECT image FROM paintings WHERE id → ajouter tenant_id
- [ ] DELETE FROM paintings WHERE id → ajouter tenant_id

**Fonction: `admin_delete_painting()` (ligne ~3600)**
- [ ] DELETE FROM paintings WHERE id → ajouter tenant_id

**Fonction: `reorder_paintings()` (ligne ~2830-2850)**
- [ ] SELECT id FROM paintings → ajouter tenant_id
- [ ] UPDATE paintings SET display_order → ajouter tenant_id

### 4. EXHIBITIONS (~10 requêtes)

#### Fichier: app.py

**Fonction: `expositions()` (ligne ~3050)**
- [ ] SELECT FROM exhibitions → ajouter tenant_id

**Fonction: `add_exhibition()` (ligne ~3100)**
- [ ] INSERT INTO exhibitions → ajouter tenant_id

**Fonction: `edit_exhibition()` (ligne ~3150)**
- [ ] SELECT FROM exhibitions WHERE id → ajouter tenant_id
- [ ] UPDATE exhibitions WHERE id → ajouter tenant_id

**Fonction: `delete_exhibition()` (ligne ~3200)**
- [ ] DELETE FROM exhibitions WHERE id → ajouter tenant_id

**Fonction: API `/api/export/exhibitions` (ligne ~4450)**
- [ ] SELECT FROM exhibitions → ajouter tenant_id

### 5. CUSTOM_REQUESTS (~10 requêtes)

#### Fichier: app.py

**Fonction: `custom_order()` (ligne ~2750)**
- [ ] INSERT INTO custom_requests → ajouter tenant_id

**Fonction: `admin_custom_requests()` (ligne ~3900)**
- [ ] SELECT FROM custom_requests → ajouter tenant_id

**Fonction: `admin_custom_request_detail()` (ligne ~3950)**
- [ ] SELECT FROM custom_requests WHERE id → ajouter tenant_id
- [ ] UPDATE custom_requests WHERE id → ajouter tenant_id

**Fonction: API `/api/export/custom-requests` (ligne ~4470)**
- [ ] SELECT FROM custom_requests → ajouter tenant_id

### 6. NOTIFICATIONS (~8 requêtes)

#### Fichier: app.py

**Fonction: `inject_cart()` - section notifications (ligne ~2700)**
- [ ] SELECT COUNT FROM notifications → ajouter tenant_id

**Fonction: `admin_notifications()` (ligne ~4050)**
- [ ] SELECT FROM notifications → ajouter tenant_id
- [ ] UPDATE notifications SET is_read → ajouter tenant_id

**Fonction: `create_notification()` (si existe)**
- [ ] INSERT INTO notifications → ajouter tenant_id

### 7. SETTINGS (~8 requêtes)

#### Fichier: app.py

**Fonction: `get_setting()` (ligne ~570)**
- [ ] SELECT FROM settings WHERE key → ajouter tenant_id

**Fonction: `set_setting()` (ligne ~635-680)**
- ✅ Déjà partiellement fait mais à vérifier

**Fonction: API `/api/export/settings` (ligne ~851-900)**
- [ ] SELECT FROM settings → ajouter tenant_id

### 8. USERS ADMIN (~10 requêtes)

#### Fichier: app.py

**Fonction: `admin_users()` (ligne ~3860)**
- [ ] SELECT FROM users → ajouter tenant_id (avec filtres)

**Fonction: `admin_user_detail()` (ligne ~3050)**
- [ ] SELECT FROM users WHERE id → ajouter tenant_id

**Fonction: `admin_update_user_role()` (ligne ~3970)**
- [ ] SELECT email FROM users WHERE id → ajouter tenant_id
- [ ] UPDATE users SET role WHERE id → ajouter tenant_id

**Fonction: `set_admin_user()` (ligne ~1120)**
- [ ] UPDATE users SET role WHERE email → ajouter tenant_id

### 9. LOGIN/AUTH ADDITIONAL (~5 requêtes)

#### Fichier: app.py

**Fonction: `api_login_preview()` (ligne ~1465-1512)**
- [ ] SELECT FROM users WHERE email → ajouter tenant_id
- [ ] SELECT FROM carts WHERE user_id → ajouter tenant_id
- [ ] INSERT INTO carts → ajouter tenant_id

**Fonction: `api_register_preview()` (ligne ~1378-1420)**
- [ ] SELECT FROM users WHERE email → ajouter tenant_id
- [ ] SELECT COUNT FROM users → ajouter tenant_id
- [ ] INSERT INTO users → ajouter tenant_id

### 10. STRIPE EVENTS (~5 requêtes)

#### Fichier: app.py

**Fonction: Webhook Stripe handlers (chercher "stripe")**
- [ ] INSERT INTO stripe_events → ajouter tenant_id
- [ ] SELECT FROM stripe_events → ajouter tenant_id (si existe)

### 11. SAAS_SITES (~5 requêtes)

#### Fichier: app.py

**Fonction: SAAS endpoints (chercher "saas")**
- [ ] SELECT FROM saas_sites → ajouter tenant_id
- [ ] INSERT INTO saas_sites → ajouter tenant_id
- [ ] UPDATE saas_sites → ajouter tenant_id

## Validation Cross-Entity

Pour chaque relation entre tables, vérifier que les deux entités appartiennent au même tenant:

### Paintings ↔ Cart Items
```python
# Avant d'ajouter au panier
c.execute(adapt_query("SELECT id FROM paintings WHERE id=? AND tenant_id=?"), (painting_id, tenant_id))
if not c.fetchone():
    return error("Painting not found")
```

### Paintings ↔ Order Items
```python
# Avant de créer une commande
for item in cart_items:
    c.execute(adapt_query("SELECT id FROM paintings WHERE id=? AND tenant_id=?"), (item['painting_id'], tenant_id))
    if not c.fetchone():
        return error("Invalid painting")
```

### User ↔ Cart
```python
# Avant d'associer panier à utilisateur
c.execute(adapt_query("SELECT id FROM users WHERE id=? AND tenant_id=?"), (user_id, tenant_id))
if not c.fetchone():
    return error("User not found")
```

## Tests à Effectuer

Après toutes les modifications:

1. **Test d'isolation**: 
   - Créer 2 tenants différents
   - Ajouter des données dans chaque tenant
   - Vérifier qu'aucune donnée ne fuite entre tenants

2. **Test de requêtes**:
   - Vérifier que toutes les pages se chargent
   - Vérifier que les API endpoints retournent les bonnes données
   - Vérifier que les actions (ajout, modification, suppression) fonctionnent

3. **Test de sécurité**:
   - Tenter d'accéder à des ressources d'un autre tenant via ID direct
   - Vérifier que les JOIN ne retournent pas de données d'autres tenants

4. **Test de régression**:
   - Vérifier que l'application fonctionne pour tenant_id=1 (existant)
   - Vérifier que les migrations ne cassent rien

## Dashboard - Modifications Nécessaires

### Option Recommandée: Host-Based Tenant Resolution

**Aucune modification du Dashboard n'est requise** si:
- Le Dashboard appelle les API Template en utilisant le vrai host du site
- Example: `https://artist1.artworksdigital.fr/api/export/paintings`

Template résout automatiquement le tenant_id via `get_current_tenant_id()` qui fait:
```python
host = request.host  # "artist1.artworksdigital.fr"
SELECT id FROM tenants WHERE host = host
```

### Configuration Dashboard

Le Dashboard doit simplement:
1. Stocker le host de chaque site artiste
2. Utiliser ce host dans les requêtes API

```python
# Dashboard code
site = Site.objects.get(id=site_id)
template_host = site.domain  # "artist1.artworksdigital.fr"
api_url = f"https://{template_host}/api/export/paintings"
response = requests.get(api_url, headers={"X-API-Key": api_key})
```

**Aucune autre modification Dashboard n'est requise!**

## Checklist Finale

Avant de considérer le travail terminé:

- [ ] Toutes les requêtes mises à jour (voir sections ci-dessus)
- [ ] Migration testée sur DB de dev
- [ ] Migration testée sur DB de production
- [ ] Tests d'isolation passés (2+ tenants)
- [ ] Tests de régression passés
- [ ] Tests de sécurité passés
- [ ] Documentation Dashboard mise à jour
- [ ] Code review effectué
- [ ] Déployé en staging
- [ ] Testé en staging
- [ ] Déployé en production

## Notes Importantes

1. **Ne JAMAIS faire confiance à l'ID**: Toujours filtrer par tenant_id en plus de l'ID
2. **Valider les relations**: Avant de créer une relation entre 2 entités, vérifier qu'elles sont dans le même tenant
3. **display_order**: L'ordre d'affichage doit être isolé par tenant (déjà fait pour paintings)
4. **Backward compatibility**: Les données existantes ont tenant_id=1 par défaut
5. **Performance**: Les index sur tenant_id sont créés automatiquement par la migration

## Contact

Pour questions: voir le PR copilot/analyze-data-isolation-tenants
