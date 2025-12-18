# Migration Tenant ID - README

## Description

Ce projet contient des scripts Python pour migrer et corriger les `tenant_id` de toutes les données multi-tenant dans le système Template.

## Objectif

Récupérer les `tenant_id` depuis la table `tenants` et les appliquer à toutes les données de chaque site, en respectant strictement les règles d'isolation multi-tenant.

## Règles Strictes

1. ✅ Tous les `tenant_id` proviennent **exclusivement** de la table `tenants`
2. ❌ Le `tenant_id = 1` (défaut) est **interdit** - utiliser le tenant réel du site
3. 🔍 Identifier le `tenant_id` via domaine, slug, siteid dans la table `tenants`
4. 📝 Appliquer le `tenant_id` à **TOUTES** les données du site
5. 🔒 **NE JAMAIS** modifier les données métier, relations, clés, timestamps, IDs
6. 📊 Produire un audit complet avec tous les détails
7. ⚠️ Si ambiguïté (plusieurs `tenant_id` possibles), **arrêter** et signaler
8. 🚫 **NE JAMAIS** déduire un `tenant_id` sans validation dans `tenants`

## Fichiers

### Scripts

- **`migrate_apply_tenant_ids.py`** : Script principal de migration
- **`inspect_tenant_data.py`** : Script d'inspection de la base de données

### Documentation

- **`TENANT_MIGRATION_GUIDE.md`** : Guide complet d'utilisation (français)

## Installation

```bash
# Installer les dépendances
pip install -r requirements.txt

# Configurer la base de données
export DATABASE_URL="postgresql://user:pass@host:5432/db"
# ou
export SUPABASE_DB_URL="postgresql://user:pass@host:5432/db"
```

## Utilisation Rapide

### 1. Inspecter l'état actuel

```bash
python inspect_tenant_data.py
```

### 2. Tester la migration (dry-run)

```bash
python migrate_apply_tenant_ids.py --dry-run
```

### 3. Exécuter la migration

```bash
# ⚠️ ATTENTION: Crée une sauvegarde d'abord!
pg_dump $DATABASE_URL > backup.sql

# Exécuter la migration
python migrate_apply_tenant_ids.py
```

## Résultat

Le script génère:

- ✅ Un rapport détaillé dans le terminal
- 📄 Un fichier JSON d'audit: `tenant_migration_report_YYYYMMDD_HHMMSS.json`

### Exemple de rapport

```
================================================================================
📊 RAPPORT D'AUDIT COMPLET
================================================================================

📈 RÉSUMÉ
--------------------------------------------------------------------------------
Date d'exécution: 2024-01-25T10:30:45
Tenants trouvés: 3
Sites traités: 2
Total lignes mises à jour: 62

🏢 TENANTS TROUVÉS
--------------------------------------------------------------------------------
❌ DÉFAUT (id=1) Tenant 1: localhost (Tenant par défaut)
✅ Tenant 2: artist1.artworksdigital.fr (Artiste 1)
✅ Tenant 3: artist2.artworksdigital.fr (Artiste 2)

🌐 SITES TRAITÉS
--------------------------------------------------------------------------------

Site 1:
  Domaine: artist1.artworksdigital.fr
  Tenant: 1 → 2 (host: artist1.artworksdigital.fr)
  Match: final_domain
  Lignes mises à jour: 49
    - saas_sites: 1 ligne(s)
    - users: 1 ligne(s)
    - paintings: 15 ligne(s)
    - orders: 5 ligne(s)
    - ...

📊 MISES À JOUR PAR TABLE
--------------------------------------------------------------------------------
  users: 2 ligne(s)
  paintings: 25 ligne(s)
  orders: 5 ligne(s)
  ...
```

## Tables Concernées

Le script met à jour automatiquement les `tenant_id` dans:

- ✅ `saas_sites` - Sites eux-mêmes
- ✅ `users` - Utilisateurs propriétaires
- ✅ `paintings` - Peintures des sites
- ✅ `carts` - Paniers
- ✅ `cart_items` - Items dans les paniers
- ✅ `orders` - Commandes
- ✅ `order_items` - Items des commandes
- ✅ `favorites` - Favoris
- ✅ `notifications` - Notifications
- ✅ `custom_requests` - Demandes personnalisées
- ✅ `exhibitions` - Expositions
- ✅ `settings` - Paramètres
- ✅ `stripe_events` - Événements Stripe

## Stratégie de Mapping

### Identification du Tenant

1. **Par final_domain** (priorité 1)
   ```sql
   SELECT id FROM tenants WHERE host = saas_sites.final_domain
   ```

2. **Par sandbox_url** (priorité 2)
   ```sql
   -- Extraire le domaine de sandbox_url
   SELECT id FROM tenants WHERE host = extracted_domain
   ```

### Application des tenant_id

Pour chaque site:

1. Mettre à jour `saas_sites` (le site lui-même)
2. Mettre à jour `users` (utilisateur propriétaire)
3. Mettre à jour toutes les données liées:
   - Par `user_id` : paintings, carts, orders, favorites, etc.
   - Par relation : cart_items (via carts), order_items (via orders)
   - Par tenant : exhibitions, settings, stripe_events

## Sécurité

- ✅ **Idempotent** : Peut être relancé sans risque
- ✅ **Dry-run** : Mode test sans modification
- ✅ **Audit complet** : Rapport JSON détaillé
- ✅ **Pas de perte de données** : Seul `tenant_id` est modifié
- ✅ **Validation** : Détection des ambiguïtés et erreurs

## Gestion des Erreurs

### Erreur: "Aucun tenant correspondant trouvé"

**Solution**: Créer le tenant manquant
```sql
INSERT INTO tenants (host, name, created_at)
VALUES ('domain.com', 'Nom du Site', CURRENT_TIMESTAMP);
```

### Erreur: "AMBIGUÏTÉ: plusieurs tenants possibles"

**Solution**: Supprimer les doublons dans `tenants`
```sql
-- Identifier les doublons
SELECT host, COUNT(*) FROM tenants GROUP BY host HAVING COUNT(*) > 1;

-- Supprimer les doublons (garder le bon ID)
DELETE FROM tenants WHERE id = <id_a_supprimer>;
```

### Avertissement: "Site n'a pas de user_id"

**Solution**: Associer l'utilisateur au site
```sql
UPDATE saas_sites SET user_id = <user_id> WHERE id = <site_id>;
```

## Rollback

En cas de problème:

```bash
# Restaurer depuis la sauvegarde
psql $DATABASE_URL < backup.sql
```

## Tests Post-Migration

### Vérifier l'isolation

```sql
-- Aucune donnée ne doit avoir tenant_id NULL
SELECT 'users' as t, COUNT(*) FROM users WHERE tenant_id IS NULL
UNION ALL
SELECT 'paintings', COUNT(*) FROM paintings WHERE tenant_id IS NULL
UNION ALL
SELECT 'orders', COUNT(*) FROM orders WHERE tenant_id IS NULL;
-- Résultat attendu: 0 pour toutes les tables

-- Vérifier la distribution des tenant_id
SELECT tenant_id, COUNT(*) FROM users GROUP BY tenant_id;
SELECT tenant_id, COUNT(*) FROM paintings GROUP BY tenant_id;
```

### Test fonctionnel

1. Se connecter avec un utilisateur
2. Créer une peinture
3. Ajouter au panier
4. Créer une commande
5. Vérifier que tout fonctionne

## Documentation Complète

Consultez `TENANT_MIGRATION_GUIDE.md` pour:

- Guide détaillé pas à pas
- Exemples de sortie
- Procédures de dépannage
- Architecture du système

## Support

- 📖 Documentation : `TENANT_MIGRATION_GUIDE.md`
- 🔍 Inspection : `python inspect_tenant_data.py`
- 📊 Audit : Consulter le fichier `tenant_migration_report_*.json`

## Avertissements

⚠️ **IMPORTANT**:

1. **Toujours faire une sauvegarde** avant la migration
2. **Tester en dry-run** avant la vraie migration
3. **Vérifier les tenants** existent pour tous les sites
4. **Valider le rapport** d'audit après la migration
5. **Tester l'application** après la migration

## License

Ce projet fait partie du système Template.
