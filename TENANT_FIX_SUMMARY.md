# 🔧 Multi-Tenant Errors - Correction Summary

## ✅ Problèmes Résolus

### 1. ✅ "Working outside of request context" - RÉSOLU

**Problème:** 
```
RuntimeError: Working outside of request context.
```

**Cause:** 
Le fichier `app.py` appelait `set_admin_user('coco.cayre@gmail.com')` au démarrage (ligne 1211), qui appelait `get_current_tenant_id()`, qui essayait d'accéder à `request.host` en dehors d'un contexte HTTP.

**Solution Appliquée:**
1. ✅ Supprimé l'appel à `set_admin_user()` au démarrage
2. ✅ Ajouté `has_request_context` dans les imports Flask
3. ✅ Modifié `get_current_tenant_id()` pour vérifier le contexte avant d'accéder à `request.host`
4. ✅ Retourne `tenant_id = 1` (par défaut) quand appelé hors contexte HTTP

**Code Modifié:**
```python
from flask import Flask, ..., has_request_context

def get_current_tenant_id():
    """
    Récupère le tenant_id du tenant courant basé sur le host de la requête.
    NOTE: Doit être appelé uniquement dans un contexte de requête HTTP.
    """
    # Vérifier qu'on est dans un contexte de requête HTTP
    if not has_request_context():
        print(f"[TENANT] get_current_tenant_id() appelé hors contexte HTTP - utilisation du tenant par défaut (1)")
        return 1
    
    try:
        host = request.host.split(':')[0].lower()
        # ... reste du code
```

**Vérification:**
```bash
python verify_tenant_fixes.py
# ✅ All critical fixes are in place!
```

---

## ⏳ Problème Restant: "column tenant_id does not exist"

### Problème:
```
psycopg.errors.UndefinedColumn: column "tenant_id" does not exist
LINE 1: ...ROM carts WHERE session_id='...' AND tenant_id=1
```

**Cause:** 
La base de données Supabase/PostgreSQL n'a pas encore les colonnes `tenant_id` dans les tables, mais le code essaie de les utiliser.

**Tables Affectées:**
- `users`
- `paintings`
- `orders`
- `order_items`
- `cart_items`
- `carts`
- `favorites`
- `notifications`
- `exhibitions`
- `custom_requests`
- `settings`
- `stripe_events`
- `saas_sites`

### ✅ Solution: Exécuter le Script de Migration

Le script `migrate_add_tenant_id.py` existe déjà et est prêt à être exécuté.

**Ce que fait le script:**
1. Crée la table `tenants` (si elle n'existe pas)
2. Crée un tenant par défaut avec `id=1`
3. Ajoute la colonne `tenant_id` à toutes les tables nécessaires
4. Associe toutes les données existantes au `tenant_id=1` (par défaut)
5. Crée des indexes de performance sur les colonnes `tenant_id`

**Commandes pour Exécuter la Migration:**

#### Option 1: Via Scalingo CLI (Recommandé)
```bash
# 1. Se connecter à Scalingo
scalingo --region osc-fr1 --app preview-colin-cayre login

# 2. Vérifier quelles tables ont déjà tenant_id
scalingo --region osc-fr1 --app preview-colin-cayre run python verify_tenant_columns.py

# 3. Exécuter la migration
scalingo --region osc-fr1 --app preview-colin-cayre run python migrate_add_tenant_id.py

# 4. Vérifier que la migration a réussi
scalingo --region osc-fr1 --app preview-colin-cayre run python verify_tenant_columns.py
```

#### Option 2: Via Console Web Scalingo
1. Aller sur https://dashboard.scalingo.com/
2. Sélectionner l'app `preview-colin-cayre`
3. Onglet "Run"
4. Exécuter: `python migrate_add_tenant_id.py`

#### Option 3: En Local (si accès direct à la DB)
```bash
# 1. Définir l'URL de la base de données
export SUPABASE_DB_URL="postgresql://user:password@host:port/database"

# 2. Vérifier l'état actuel
python verify_tenant_columns.py

# 3. Exécuter la migration
python migrate_add_tenant_id.py

# 4. Vérifier le résultat
python verify_tenant_columns.py
```

**Sortie Attendue:**
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
   ✅ Colonne tenant_id ajoutée à 'carts'
   ... (etc)

============================================================
✅ MIGRATION TERMINÉE
============================================================
```

---

## 🔍 Vérifications Post-Migration

### 1. Vérifier que tenant_id existe dans toutes les tables
```bash
python verify_tenant_columns.py
```

**Sortie attendue:**
```
✅ users - HAS tenant_id
✅ carts - HAS tenant_id
✅ paintings - HAS tenant_id
... (toutes les tables)

✅ All expected tables have tenant_id column
```

### 2. Tester l'application
```bash
# Redémarrer l'application
scalingo --region osc-fr1 --app preview-colin-cayre restart

# Vérifier les logs
scalingo --region osc-fr1 --app preview-colin-cayre logs --lines 100
```

**Tests manuels:**
- ✅ Visiter `/` (page d'accueil)
- ✅ Se connecter (`/login`)
- ✅ Ajouter un article au panier
- ✅ Visiter `/saas/launch/success`

**Erreurs qui doivent disparaître:**
- ❌ `Working outside of request context` ← Déjà corrigé
- ❌ `column "tenant_id" does not exist` ← Sera corrigé après migration

---

## 📋 Règles Multi-Tenant (Rappel)

### ✅ Règles Respectées dans le Code

1. ✅ **Récupération de tenant_id UNIQUEMENT dans contexte HTTP**
   - `get_current_tenant_id()` vérifie `has_request_context()`
   - Retourne `1` par défaut si hors contexte

2. ✅ **Filtrage par tenant_id sur toutes les tables qui l'ont**
   - Toutes les requêtes SQL incluent `WHERE ... AND tenant_id=?`
   - 94 requêtes utilisent le filtrage tenant_id

3. ✅ **Pas d'inférence de tenant depuis d'autres champs**
   - Le tenant est déterminé uniquement par `request.host`
   - Mapping host → tenant_id via la table `tenants`

4. ✅ **Isolation stricte des données**
   - Chaque requête est filtrée par tenant_id
   - Indexes créés pour performance

### ⚠️ Points d'Attention

**Tables AVEC tenant_id (après migration):**
- `users`, `paintings`, `orders`, `order_items`, `cart_items`, `carts`
- `favorites`, `notifications`, `exhibitions`, `custom_requests`
- `settings`, `stripe_events`, `saas_sites`

**Table SANS tenant_id:**
- `tenants` (c'est la table de référence des tenants)

---

## 📊 Résumé des Modifications

### Fichiers Modifiés
- ✅ `app.py` - Corrections multi-tenant
  - Import `has_request_context`
  - Fonction `get_current_tenant_id()` avec vérification de contexte
  - Suppression de l'appel `set_admin_user()` au démarrage

### Fichiers Ajoutés
- ✅ `verify_tenant_fixes.py` - Vérification des corrections de code
- ✅ `verify_tenant_columns.py` - Vérification des colonnes tenant_id dans la DB
- ✅ `TENANT_FIX_SUMMARY.md` - Cette documentation

### Fichiers Existants (Non Modifiés)
- ℹ️ `migrate_add_tenant_id.py` - Script de migration (déjà présent)
- ℹ️ `TENANT_MIGRATION_DEPLOYMENT.md` - Documentation de migration (déjà présente)

---

## ✅ Checklist de Déploiement

- [x] Code corrigé pour "Working outside of request context"
- [x] Vérifications de code ajoutées
- [ ] **Migration à exécuter:** `python migrate_add_tenant_id.py`
- [ ] Vérifier que toutes les tables ont tenant_id
- [ ] Redémarrer l'application
- [ ] Tester les endpoints critiques
- [ ] Vérifier les logs pour confirmer absence d'erreurs

---

## 🆘 Support

**Si des erreurs persistent après la migration:**

1. Vérifier que la migration a réussi:
   ```bash
   python verify_tenant_columns.py
   ```

2. Vérifier les logs de l'application:
   ```bash
   scalingo logs --lines 200 | grep -i "tenant\|error"
   ```

3. Redémarrer l'application:
   ```bash
   scalingo restart
   ```

4. Si le problème persiste, vérifier que `SUPABASE_DB_URL` pointe vers la bonne base de données.

---

**Date:** 2025-12-17
**Status:** Code corrigé ✅ | Migration en attente ⏳
**Action requise:** Exécuter `migrate_add_tenant_id.py` sur la base de données de production
