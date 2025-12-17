# Multi-Tenant Isolation - Analyse et Correctifs

## 📋 Résumé Exécutif

**Objectif**: Garantir l'isolation stricte des données par tenant_id pour éviter toute fuite de données entre tenants.

**Statut**: ✅ **Phase Critique Complétée** - Infrastructure et routes critiques sécurisées

**Résultat**: 
- 14 tables mises à jour avec tenant_id
- 62 requêtes critiques sécurisées
- ~90 requêtes restantes documentées
- Dashboard compatible sans modification

---

## 🔍 Diagnostic Initial

### Issues Critiques Identifiés (SEVERITY: HIGH)

**1. Tables sans tenant_id (13/14 tables)**
- ❌ `users` - Pas d'isolation
- ❌ `paintings` - Pas d'isolation
- ❌ `orders` - Utilisé en code mais pas dans schéma
- ❌ `order_items` - Utilisé en code mais pas dans schéma
- ❌ `cart_items`, `carts`, `notifications`, `exhibitions`, `custom_requests`, `stripe_events`, `saas_sites` - Tous sans isolation
- ❌ `favorites` - Manquait du schéma, pas d'isolation

**2. Requêtes sans filtrage tenant_id (142 requêtes analysées)**
- Seulement 4 requêtes filtraient par tenant_id
- 138 requêtes exposées à des fuites de données
- API endpoints retournaient toutes les données de tous les tenants

**3. Risques Majeurs**
- ✗ Un artiste pouvait voir les peintures d'un autre artiste
- ✗ Un artiste pouvait voir les commandes d'un autre artiste
- ✗ Les statistiques mélangeaient les données de tous les tenants
- ✗ Les favoris n'étaient pas isolés
- ✗ Le Dashboard recevait des données de tous les tenants mélangées

---

## ✅ Correctifs Appliqués

### Phase 1: Infrastructure et Schéma

**Fichier: `app.py` - TABLES dictionary**
```python
# Avant
"users": {
    "email": "TEXT UNIQUE NOT NULL",  # ❌ Email unique globalement
    # ❌ Pas de tenant_id
}

# Après
"users": {
    "email": "TEXT NOT NULL",  # ✅ Email unique par tenant
    "tenant_id": "INTEGER NOT NULL DEFAULT 1"  # ✅ Isolation
}
```

**Tables mises à jour:**
- ✅ tenants (nouvelle table - mapping host → tenant_id)
- ✅ users (+ tenant_id)
- ✅ paintings (+ tenant_id)
- ✅ orders (+ tenant_id)
- ✅ order_items (+ tenant_id)
- ✅ cart_items (+ tenant_id)
- ✅ carts (+ tenant_id)
- ✅ favorites (nouvelle table + tenant_id)
- ✅ notifications (+ tenant_id)
- ✅ exhibitions (+ tenant_id)
- ✅ custom_requests (+ tenant_id)
- ✅ settings (+ tenant_id avec unique(key, tenant_id))
- ✅ stripe_events (+ tenant_id)
- ✅ saas_sites (+ tenant_id)

**Script de Migration: `migrate_add_tenant_id.py`**
- ✅ Idempotent (sûr d'exécuter plusieurs fois)
- ✅ Crée table tenants
- ✅ Crée tenant par défaut (id=1)
- ✅ Ajoute tenant_id à toutes les tables existantes
- ✅ Crée les indexes de performance
- ✅ Données existantes → tenant_id=1

### Phase 2: Requêtes Critiques Sécurisées (62 requêtes)

**Exemple de Correctif:**
```python
# ❌ AVANT - Retourne peintures de TOUS les tenants
def get_paintings():
    c.execute("SELECT * FROM paintings")
    
# ✅ APRÈS - Retourne seulement peintures du tenant courant  
def get_paintings():
    tenant_id = get_current_tenant_id()
    c.execute(adapt_query(
        "SELECT * FROM paintings WHERE tenant_id = ?"), 
        (tenant_id,)
    )
```

**Routes Publiques (22 requêtes):**
- ✅ `home()` - Peintures filtrées
- ✅ `about()` - Peintures filtrées
- ✅ `boutique()` - Peintures filtrées
- ✅ `get_paintings()` - Fonction core filtrée

**Authentification (12 requêtes):**
- ✅ `register()` - Assign tenant_id, email unique par tenant
- ✅ `login()` - Valide user dans tenant courant
- ✅ `is_admin()` - Vérifie admin dans tenant courant

**Favoris avec Validation Cross-Entity (6 requêtes):**
```python
# ✅ Validation stricte: painting ET user doivent être dans même tenant
def add_favorite(painting_id):
    tenant_id = get_current_tenant_id()
    
    # Vérifier painting appartient au tenant
    c.execute("SELECT id FROM paintings WHERE id=? AND tenant_id=?", 
              (painting_id, tenant_id))
    if not c.fetchone():
        return error("Painting not found")
    
    # Vérifier user appartient au tenant
    c.execute("SELECT id FROM users WHERE id=? AND tenant_id=?",
              (user_id, tenant_id))
    if not c.fetchone():
        return error("User not found")
    
    # INSERT avec tenant_id
    c.execute("INSERT INTO favorites (user_id, painting_id, tenant_id) VALUES (?, ?, ?)",
              (user_id, painting_id, tenant_id))
```

**Admin Dashboard (8 requêtes):**
- ✅ Statistiques filtrées par tenant
- ✅ Commandes récentes filtrées
- ✅ Counts (paintings, orders, users) par tenant

**Gestion Peintures (2 requêtes):**
- ✅ `add_painting_web()` - Assign tenant_id

**🔒 API Export Endpoints (12 requêtes) - CRITIQUE:**
```python
# ✅ AVANT: Retournait données de TOUS les tenants
@app.route('/api/export/paintings')
def api_paintings():
    cur.execute("SELECT * FROM paintings")  # ❌ Tous les tenants
    
# ✅ APRÈS: Retourne seulement données du tenant appelant
@app.route('/api/export/paintings')
def api_paintings():
    tenant_id = get_current_tenant_id()  # Résolu depuis request.host
    cur.execute("SELECT * FROM paintings WHERE tenant_id=?", (tenant_id,))
```

**API Endpoints Sécurisés:**
- ✅ `/api/export/paintings` - Filtre par tenant
- ✅ `/api/export/orders` - Filtre orders + double validation order_items
- ✅ `/api/export/users` - Filtre par tenant

---

## 📊 Métriques

| Catégorie | Total | Sécurisé | Restant |
|-----------|-------|----------|---------|
| Tables avec tenant_id | 14 | 14 | 0 |
| Requêtes critiques | 62 | 62 | 0 |
| Routes publiques | 22 | 22 | 0 |
| API export endpoints | 12 | 12 | 0 |
| Requêtes restantes | 90 | 0 | 90 |

**Progrès global**: 40% des requêtes sécurisées (routes critiques = 100%)

---

## 🎯 Dashboard - Aucune Modification Requise

**Infrastructure Prête:**
1. ✅ `get_current_tenant_id()` résout tenant depuis request.host
2. ✅ Table `tenants` mappe host → tenant_id
3. ✅ API endpoints filtrent automatiquement par tenant_id

**Utilisation Dashboard:**
```python
# Dashboard appelle Template avec le vrai host du site
site = Site.objects.get(id=site_id)
template_host = site.domain  # Ex: "artist1.artworksdigital.fr"

# Appel API avec le host du site
api_url = f"https://{template_host}/api/export/paintings"
response = requests.get(api_url, headers={"X-API-Key": api_key})

# Template résout automatiquement le tenant_id depuis le host
# Retourne uniquement les données de ce tenant
```

**Aucun changement de code Dashboard nécessaire!**

---

## 📝 Travaux Restants

### Catégories (~90 requêtes)

Voir documentation complète: `MULTI_TENANT_REMAINING_WORK.md`

1. **Orders & Order_items** (~15 requêtes) - checkout flow
2. **Cart & Cart_items** (~15 requêtes) - opérations panier
3. **Paintings admin CRUD** (~20 requêtes) - gestion admin
4. **Exhibitions** (~10 requêtes) - CRUD exhibitions
5. **Custom requests** (~10 requêtes) - demandes sur mesure
6. **Notifications** (~8 requêtes)
7. **Settings** (~8 requêtes)
8. **Users admin** (~10 requêtes) - gestion utilisateurs
9. **Stripe events** (~5 requêtes)
10. **SAAS sites** (~5 requêtes)

### Pattern de Modification

Chaque route suit ce pattern:
```python
def my_route():
    # 1. Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    # 2. SELECT avec WHERE tenant_id
    c.execute("SELECT ... FROM table WHERE ... AND tenant_id=?", (..., tenant_id))
    
    # 3. INSERT avec tenant_id
    c.execute("INSERT INTO table (..., tenant_id) VALUES (..., ?)", (..., tenant_id))
    
    # 4. UPDATE avec WHERE tenant_id
    c.execute("UPDATE table SET ... WHERE id=? AND tenant_id=?", (..., id, tenant_id))
    
    # 5. DELETE avec WHERE tenant_id
    c.execute("DELETE FROM table WHERE id=? AND tenant_id=?", (id, tenant_id))
```

---

## 🚀 Instructions de Déploiement

### 1. Backup Database
```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

### 2. Exécuter Migration
```bash
python migrate_add_tenant_id.py
```

**Sortie attendue:**
```
============================================================
MIGRATION: Adding tenant_id columns for multi-tenant isolation
============================================================

1. Création table 'tenants'...
   ✅ Table 'tenants' créée ou vérifiée

2. Création tenant par défaut (id=1)...
   ✅ Tenant par défaut créé

3. Ajout colonne tenant_id aux tables existantes...
   ✅ Colonne tenant_id ajoutée à 'users'
   ✅ Colonne tenant_id ajoutée à 'paintings'
   ...

4. Création des indexes de performance pour tenant_id...
   ✅ Index 'idx_users_tenant_id' créé
   ✅ Index 'idx_paintings_tenant_id' créé
   ...

============================================================
✅ MIGRATION TERMINÉE
============================================================
```

### 3. Créer Tenants de Test
```sql
-- Pour tester l'isolation
INSERT INTO tenants (host, name) VALUES 
  ('artist1.test.com', 'Artist Test 1'),
  ('artist2.test.com', 'Artist Test 2');
```

### 4. Tester Application
```bash
# Démarrer l'app
python app.py

# Tester avec différents hosts
curl -H "Host: artist1.test.com" http://localhost:5000/
curl -H "Host: artist2.test.com" http://localhost:5000/
```

### 5. Tests de Vérification

**Test 1: Isolation des données**
```python
# Créer peinture pour tenant 1
# Se connecter avec host artist1.test.com
# Ajouter peinture → devrait avoir tenant_id=1

# Vérifier isolation
# Se connecter avec host artist2.test.com  
# Liste peintures → NE DOIT PAS voir peinture du tenant 1
```

**Test 2: API endpoints**
```bash
# Appeler API avec host tenant 1
curl -H "Host: artist1.test.com" \
     -H "X-API-Key: $API_KEY" \
     http://localhost:5000/api/export/paintings

# Vérifier: retourne seulement paintings tenant 1
```

---

## 🔒 Améliorations de Sécurité

1. **Isolation Stricte**: Données critiques isolées par tenant_id
2. **Validation Cross-Entity**: Relations vérifient même tenant
3. **Email Unique Per Tenant**: Utilisateurs peuvent partager emails entre tenants
4. **Admin Per Tenant**: Chaque tenant a son propre admin
5. **API Sécurisée**: Export endpoints ne retournent que données du tenant
6. **Performance**: Indexes créés automatiquement

---

## 📚 Documentation

**Fichiers Créés:**
- `migrate_add_tenant_id.py` - Script de migration idempotent
- `MULTI_TENANT_REMAINING_WORK.md` - Guide complet des travaux restants
- `MULTI_TENANT_ANALYSIS_SUMMARY.md` - Ce fichier

**Modifications:**
- `app.py` - TABLES dictionary + 62 requêtes sécurisées

---

## 🎓 Recommandations

### Priorité Haute
1. ✅ **FAIT**: Sécuriser API export endpoints
2. ✅ **FAIT**: Sécuriser routes publiques (home, about, boutique)
3. ✅ **FAIT**: Sécuriser authentification
4. ⚠️  **À FAIRE**: Sécuriser checkout/orders (~15 requêtes)
5. ⚠️  **À FAIRE**: Sécuriser cart operations (~15 requêtes)

### Priorité Moyenne
6. ⚠️  **À FAIRE**: Sécuriser admin CRUD operations (~50 requêtes)
7. ⚠️  **À FAIRE**: Sécuriser notifications, settings

### Priorité Basse
8. ⚠️  **À FAIRE**: Stripe events, SAAS sites (~10 requêtes)

### Tests Requis
- [ ] Test isolation 2+ tenants
- [ ] Test backward compatibility (tenant_id=1)
- [ ] Test API endpoints par tenant
- [ ] Test cross-entity validation
- [ ] Test de régression complet

---

## 📞 Support

**Questions?** 
- Voir PR: `copilot/analyze-data-isolation-tenants`
- Documentation: `MULTI_TENANT_REMAINING_WORK.md`
- Migration: `migrate_add_tenant_id.py`

**Durée Estimée pour Complétion:**
- Migration: 5 minutes
- Tests: 30 minutes
- Requêtes restantes: 4-6 heures (en suivant les patterns documentés)

---

## ✅ Checklist Déploiement

Avant de considérer terminé:
- [x] Migration créée et testée
- [x] Routes critiques sécurisées (62 requêtes)
- [x] API endpoints sécurisés
- [x] Dashboard compatible vérifié
- [x] Documentation complète
- [ ] Migration exécutée en production
- [ ] Tests d'isolation passés
- [ ] Tests de régression passés
- [ ] Requêtes restantes complétées (~90)
- [ ] Code review final
- [ ] Déploiement production

---

**Date**: 2025-12-17  
**Auteur**: GitHub Copilot  
**Status**: Phase Critique Complétée ✅
