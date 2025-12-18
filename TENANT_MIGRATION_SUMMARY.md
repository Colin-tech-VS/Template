# Migration Tenant ID - Résumé Complet

## 🎯 Objectif

Récupérer les `tenant_id` depuis la table `tenants` et les appliquer à toutes les données de chaque site, en respectant strictement les règles d'isolation multi-tenant.

## 📋 Règles Strictes Respectées

| # | Règle | Status |
|---|-------|--------|
| 1 | Tous les `tenant_id` proviennent **exclusivement** de la table `tenants` | ✅ |
| 2 | Le `tenant_id = 1` (défaut) est **interdit** - utiliser le tenant réel du site | ✅ |
| 3 | Identifier le `tenant_id` via domaine, slug, siteid dans la table `tenants` | ✅ |
| 4 | Appliquer le `tenant_id` à **TOUTES** les données du site | ✅ |
| 5 | **NE JAMAIS** modifier les données métier, relations, clés, timestamps, IDs | ✅ |
| 6 | Produire un audit complet avec tous les détails | ✅ |
| 7 | Si ambiguïté (plusieurs `tenant_id` possibles), **arrêter** et signaler | ✅ |
| 8 | **NE JAMAIS** déduire un `tenant_id` sans validation dans `tenants` | ✅ |

## 📁 Fichiers Créés

### Scripts Python

| Fichier | Description | Ligne de commande |
|---------|-------------|-------------------|
| `migrate_apply_tenant_ids.py` | Script principal de migration | `python migrate_apply_tenant_ids.py [--dry-run]` |
| `inspect_tenant_data.py` | Inspection de la base de données | `python inspect_tenant_data.py` |

### Documentation

| Fichier | Description | Contenu |
|---------|-------------|---------|
| `TENANT_MIGRATION_GUIDE.md` | Guide complet d'utilisation | 750+ lignes, français |
| `TENANT_MIGRATION_README.md` | Quick start | 350+ lignes, français |
| `SECURITY_SUMMARY_TENANT_MIGRATION.md` | Analyse de sécurité | Détails complets |
| `TENANT_MIGRATION_SUMMARY.md` | Ce fichier | Résumé exécutif |

## 🚀 Utilisation Rapide

### 1. Inspecter

```bash
python inspect_tenant_data.py
```

**Affiche:**
- Tous les tenants
- Tous les sites
- Statistiques par table

### 2. Tester (Dry-Run)

```bash
python migrate_apply_tenant_ids.py --dry-run
```

**Simule** la migration sans modifier la base.

### 3. Exécuter

```bash
# ⚠️ Créer une sauvegarde d'abord!
pg_dump $DATABASE_URL > backup.sql

# Exécuter la migration
python migrate_apply_tenant_ids.py
```

## 📊 Résultats

### Rapport Console

```
================================================================================
📊 RAPPORT D'AUDIT COMPLET
================================================================================

📈 RÉSUMÉ
Tenants trouvés: 3
Sites traités: 2
Total lignes mises à jour: 62

🏢 TENANTS TROUVÉS
✅ Tenant 2: artist1.artworksdigital.fr (Artiste 1)
✅ Tenant 3: artist2.artworksdigital.fr (Artiste 2)

🌐 SITES TRAITÉS
Site 1: 1 → 2 (49 lignes)
Site 2: 1 → 3 (13 lignes)

📊 MISES À JOUR PAR TABLE
  users: 2 ligne(s)
  paintings: 25 ligne(s)
  orders: 5 ligne(s)
  ...
```

### Rapport JSON

Fichier: `tenant_migration_report_YYYYMMDD_HHMMSS.json`

Contient:
- Liste complète des tenants
- Détails de chaque site traité
- Statistiques par table
- Anomalies et avertissements
- Erreurs rencontrées

## 🔍 Tables Mises à Jour

Le script met à jour automatiquement:

| Table | Description | Stratégie |
|-------|-------------|-----------|
| `saas_sites` | Sites eux-mêmes | Par ID du site |
| `users` | Utilisateurs propriétaires | Par user_id |
| `paintings` | Peintures des sites | Par user_id ou tenant |
| `carts` | Paniers | Par user_id |
| `cart_items` | Items dans les paniers | Via carts |
| `orders` | Commandes | Par user_id |
| `order_items` | Items des commandes | Via orders |
| `favorites` | Favoris | Par user_id |
| `notifications` | Notifications | Par user_id |
| `custom_requests` | Demandes personnalisées | Par user_id ou tenant |
| `exhibitions` | Expositions | Par tenant |
| `settings` | Paramètres | Par tenant |
| `stripe_events` | Événements Stripe | Par tenant |

## 🎯 Stratégie de Migration

### Identification du Tenant

```
1. Par final_domain (priorité 1)
   tenants.host = saas_sites.final_domain
   
2. Par sandbox_url (priorité 2)
   tenants.host = extract_domain(saas_sites.sandbox_url)
   
3. Validation
   - Un seul tenant doit correspondre
   - Si plusieurs ou aucun: signaler et arrêter
```

### Application du tenant_id

```
Pour chaque site:
  1. Mettre à jour saas_sites (le site)
  2. Mettre à jour users (propriétaire)
  3. Mettre à jour données par user_id:
     - paintings, carts, orders, favorites, notifications, custom_requests
  4. Mettre à jour données par relation:
     - cart_items (via carts), order_items (via orders)
  5. Mettre à jour données par tenant:
     - exhibitions, settings, stripe_events
```

## 🛡️ Sécurité

### Scan CodeQL

✅ **0 Alerts** - Aucune vulnérabilité détectée

### Protections

| Protection | Status | Description |
|------------|--------|-------------|
| Requêtes paramétrées | ✅ | Prévient les injections SQL |
| Whitelist des tables | ✅ | Limite les tables modifiables |
| Validation des entrées | ✅ | Vérifie tous les paramètres |
| Mode dry-run | ✅ | Test sans modification |
| Idempotence | ✅ | Sûr de relancer |
| Audit complet | ✅ | Traçabilité totale |

## ⚠️ Prérequis

### Base de Données

1. **Table `tenants` peuplée**
   ```sql
   -- Chaque site doit avoir un tenant
   INSERT INTO tenants (host, name, created_at)
   VALUES ('artist1.artworksdigital.fr', 'Artiste 1', CURRENT_TIMESTAMP);
   ```

2. **Correspondance domaines**
   - `tenants.host` = `saas_sites.final_domain`
   - Ou correspondance avec `sandbox_url`

3. **user_id dans saas_sites**
   ```sql
   -- Chaque site doit avoir un propriétaire
   UPDATE saas_sites SET user_id = X WHERE id = Y;
   ```

### Environnement

```bash
# Variable d'environnement requise
export DATABASE_URL="postgresql://user:pass@host:5432/db"
# ou
export SUPABASE_DB_URL="postgresql://user:pass@host:5432/db"

# Dépendances Python
pip install -r requirements.txt
```

## 📝 Checklist Complète

### Avant Migration

- [ ] Lire `TENANT_MIGRATION_GUIDE.md`
- [ ] Vérifier que tous les tenants existent
- [ ] Vérifier les correspondances domaines
- [ ] Créer une sauvegarde de la base
- [ ] Tester en staging

### Pendant Migration

- [ ] Exécuter `inspect_tenant_data.py`
- [ ] Exécuter `--dry-run` mode
- [ ] Vérifier le rapport dry-run
- [ ] Si OK, exécuter la vraie migration
- [ ] Surveiller la console pour erreurs

### Après Migration

- [ ] Consulter le rapport JSON
- [ ] Exécuter `inspect_tenant_data.py` à nouveau
- [ ] Vérifier les tenant_id mis à jour
- [ ] Tester l'application
- [ ] Vérifier l'isolation multi-tenant
- [ ] Surveiller les logs

## 🔧 Dépannage

### Erreur: "Aucun tenant correspondant"

**Solution:**
```sql
INSERT INTO tenants (host, name, created_at)
VALUES ('domain.com', 'Nom', CURRENT_TIMESTAMP);
```

### Erreur: "AMBIGUÏTÉ"

**Solution:**
```sql
-- Trouver les doublons
SELECT host, COUNT(*) FROM tenants GROUP BY host HAVING COUNT(*) > 1;

-- Supprimer les doublons
DELETE FROM tenants WHERE id = <id_mauvais>;
```

### Avertissement: "Site sans user_id"

**Solution:**
```sql
UPDATE saas_sites SET user_id = <user_id> WHERE id = <site_id>;
```

## 📈 Métriques de Succès

| Métrique | Cible | Comment Vérifier |
|----------|-------|------------------|
| Sites migrés | 100% | Rapport JSON |
| Erreurs | 0 | Rapport JSON |
| Tenant_id = 1 | 0 (sauf défaut) | `inspect_tenant_data.py` |
| Données perdues | 0 | Comparaison avant/après |
| Isolation | 100% | Tests fonctionnels |

## 📞 Support

### Documentation

- **Guide complet**: `TENANT_MIGRATION_GUIDE.md`
- **Quick start**: `TENANT_MIGRATION_README.md`
- **Sécurité**: `SECURITY_SUMMARY_TENANT_MIGRATION.md`

### Commandes Utiles

```bash
# Inspection
python inspect_tenant_data.py

# Test (simulation)
python migrate_apply_tenant_ids.py --dry-run

# Sauvegarde
pg_dump $DATABASE_URL > backup.sql

# Restauration
psql $DATABASE_URL < backup.sql
```

## ✅ Validation Finale

### Tests à Effectuer

1. **Isolation multi-tenant**
   - Se connecter avec utilisateur tenant A
   - Vérifier qu'il ne voit que ses données
   - Se connecter avec utilisateur tenant B
   - Vérifier qu'il ne voit que ses données

2. **Fonctionnalité**
   - Créer une peinture
   - Ajouter au panier
   - Créer une commande
   - Vérifier que tout fonctionne

3. **Base de données**
   ```sql
   -- Aucune donnée avec tenant_id NULL
   SELECT COUNT(*) FROM users WHERE tenant_id IS NULL;
   -- Doit retourner 0
   
   -- Distribution correcte
   SELECT tenant_id, COUNT(*) FROM users GROUP BY tenant_id;
   -- Doit correspondre aux sites
   ```

## 🎉 Résumé

Ce projet fournit une solution complète, sécurisée et documentée pour:

✅ Récupérer les `tenant_id` depuis la table `tenants`
✅ Mapper chaque site à son tenant correct
✅ Appliquer les `tenant_id` à toutes les données
✅ Générer un audit complet
✅ Respecter toutes les règles strictes
✅ Protéger contre les injections SQL
✅ Permettre des tests sûrs (dry-run)

---

**Date**: 2024-12-18  
**Status**: ✅ PRÊT POUR PRODUCTION  
**Sécurité**: ✅ APPROUVÉ (0 vulnérabilités)  
**Documentation**: ✅ COMPLÈTE
