# Guide de Migration des Tenant IDs

## Vue d'ensemble

Ce guide explique comment utiliser les scripts de migration pour appliquer les `tenant_id` corrects à toutes les données de chaque site, en respectant strictement les règles d'isolation multi-tenant.

## Règles Strictes

1. **Tous les `tenant_id` DOIVENT venir exclusivement de la table `tenants`**
   - Aucun tenant_id ne doit être inventé, déduit ou réutilisé depuis d'autres tables

2. **Le `tenant_id = 1` (tenant par défaut) est INTERDIT**
   - Vous devez obligatoirement utiliser le tenant_id correspondant au site réel

3. **Identification du tenant**
   - Pour chaque site, identifier son tenant_id dans la table `tenants` via domaine, slug, siteid ou clé
   - Si une correspondance manque, elle doit être signalée explicitement

4. **Application complète**
   - Une fois le bon tenant_id identifié, il doit être appliqué à TOUTES les données du site
   - Aucune ligne ne doit rester sans tenant_id ou avec un tenant_id incorrect

5. **Préservation des données**
   - NE JAMAIS modifier les données métier, les relations, les clés primaires, les timestamps ou les IDs
   - Seul le champ `tenant_id` peut être modifié

6. **Audit complet**
   - Liste des sites trouvés
   - Leur tenant_id (≠ 1)
   - Les tables mises à jour
   - Le nombre de lignes modifiées par table
   - Les éventuelles anomalies détectées

7. **Gestion des ambiguïtés**
   - Si un site possède plusieurs tenant_id potentiels, arrêter l'opération
   - Signaler l'ambiguïté et proposer une résolution

8. **Pas de déduction**
   - NE JAMAIS déduire un tenant_id à partir d'un nom, slug ou pattern
   - Validation explicite dans la table `tenants` obligatoire

## Scripts Disponibles

### 1. `inspect_tenant_data.py`

Script d'inspection pour visualiser l'état actuel de la base de données.

**Utilisation:**
```bash
python inspect_tenant_data.py
```

**Ce script affiche:**
- Tous les tenants dans la table `tenants`
- Tous les sites dans la table `saas_sites`
- Statistiques par table avec comptage par tenant_id

**Exemple de sortie:**
```
================================================================================
INSPECTION DE LA BASE DE DONNÉES
================================================================================

📋 TABLE TENANTS
--------------------------------------------------------------------------------
Nombre de tenants: 3

  ID: 1
  Host: localhost
  Name: Tenant par défaut
  Created: 2024-01-01 00:00:00

  ID: 2
  Host: artist1.artworksdigital.fr
  Name: Artiste 1
  Created: 2024-01-15 10:30:00

  ID: 3
  Host: artist2.artworksdigital.fr
  Name: Artiste 2
  Created: 2024-01-20 14:45:00

📋 TABLE SAAS_SITES
--------------------------------------------------------------------------------
Nombre de sites: 2

  Site ID: 1
  User ID: 5
  Status: active
  Sandbox URL: https://sandbox-artist1.artworksdigital.fr
  Final Domain: artist1.artworksdigital.fr
  Tenant ID: 1
  Created: 2024-01-15 10:30:00

  Site ID: 2
  User ID: 8
  Status: active
  Sandbox URL: https://sandbox-artist2.artworksdigital.fr
  Final Domain: artist2.artworksdigital.fr
  Tenant ID: 1
  Created: 2024-01-20 14:45:00

📊 STATISTIQUES PAR TABLE
--------------------------------------------------------------------------------
  users: tenant_id=1: 10 ligne(s)
  paintings: tenant_id=1: 25 ligne(s)
  orders: tenant_id=1: 8 ligne(s)
  ...
```

### 2. `migrate_apply_tenant_ids.py`

Script de migration principal pour appliquer les tenant_id corrects.

**Utilisation en mode dry-run (simulation):**
```bash
python migrate_apply_tenant_ids.py --dry-run
```

**Utilisation en mode réel:**
```bash
python migrate_apply_tenant_ids.py
```

**Options:**
- `--dry-run` : Mode simulation sans modification de la base de données

**Ce script:**
1. Récupère tous les tenants depuis la table `tenants`
2. Récupère tous les sites depuis la table `saas_sites`
3. Pour chaque site:
   - Identifie son tenant via `final_domain` ou `sandbox_url`
   - Vérifie qu'il n'y a pas d'ambiguïté
   - Applique le tenant_id à:
     - `saas_sites` (le site lui-même)
     - `users` (l'utilisateur propriétaire)
     - `paintings` (toutes les peintures du site)
     - `carts` et `cart_items` (paniers de l'utilisateur)
     - `orders` et `order_items` (commandes de l'utilisateur)
     - `favorites` (favoris de l'utilisateur)
     - `notifications` (notifications de l'utilisateur)
     - `custom_requests` (demandes personnalisées)
     - `exhibitions` (expositions du site)
     - `settings` (paramètres du tenant)
     - `stripe_events` (événements Stripe du tenant)
4. Génère un rapport d'audit complet

**Exemple de sortie:**
```
================================================================================
MIGRATION DES TENANT_ID - ISOLATION MULTI-TENANT
================================================================================

📋 ÉTAPE 1: Récupération des tenants depuis la table 'tenants'
--------------------------------------------------------------------------------
  Tenant trouvé: id=1, host=localhost, name=Tenant par défaut
  Tenant trouvé: id=2, host=artist1.artworksdigital.fr, name=Artiste 1
  Tenant trouvé: id=3, host=artist2.artworksdigital.fr, name=Artiste 2

✅ 3 tenant(s) trouvé(s)

📋 ÉTAPE 2: Récupération des sites depuis 'saas_sites'
--------------------------------------------------------------------------------

✅ 2 site(s) trouvé(s)

📋 ÉTAPE 3: Identification et application des tenant_id
--------------------------------------------------------------------------------

================================================================================
Traitement du site 1
  User ID: 5
  Domaine: artist1.artworksdigital.fr
  Sandbox: https://sandbox-artist1.artworksdigital.fr
  Tenant actuel: 1
  Nouveau tenant: 2 (host: artist1.artworksdigital.fr)
  Match via: final_domain
================================================================================
  ✅ saas_sites: 1 ligne(s) mise(s) à jour
  ✅ users: 1 ligne(s) mise(s) à jour
  ✅ paintings: 15 ligne(s) mise(s) à jour
  ✅ carts: 2 ligne(s) mise(s) à jour
  ✅ cart_items: 3 ligne(s) mise(s) à jour
  ✅ orders: 5 ligne(s) mise(s) à jour
  ✅ order_items: 8 ligne(s) mise(s) à jour
  ✅ favorites: 2 ligne(s) mise(s) à jour
  ✅ notifications: 1 ligne(s) mise(s) à jour
  ✅ settings: 12 ligne(s) mise(s) à jour

================================================================================
Traitement du site 2
  User ID: 8
  Domaine: artist2.artworksdigital.fr
  Sandbox: https://sandbox-artist2.artworksdigital.fr
  Tenant actuel: 1
  Nouveau tenant: 3 (host: artist2.artworksdigital.fr)
  Match via: final_domain
================================================================================
  ✅ saas_sites: 1 ligne(s) mise(s) à jour
  ✅ users: 1 ligne(s) mise(s) à jour
  ✅ paintings: 10 ligne(s) mise(s) à jour
  ...

================================================================================
📊 RAPPORT D'AUDIT COMPLET
================================================================================

📈 RÉSUMÉ
--------------------------------------------------------------------------------
Date d'exécution: 2024-01-25T10:30:45.123456
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
    - carts: 2 ligne(s)
    - cart_items: 3 ligne(s)
    - orders: 5 ligne(s)
    - order_items: 8 ligne(s)
    - favorites: 2 ligne(s)
    - notifications: 1 ligne(s)
    - settings: 12 ligne(s)

Site 2:
  Domaine: artist2.artworksdigital.fr
  Tenant: 1 → 3 (host: artist2.artworksdigital.fr)
  Match: final_domain
  Lignes mises à jour: 13
    - saas_sites: 1 ligne(s)
    - users: 1 ligne(s)
    - paintings: 10 ligne(s)
    - settings: 1 ligne(s)

📊 MISES À JOUR PAR TABLE
--------------------------------------------------------------------------------
  saas_sites: 2 ligne(s)
  users: 2 ligne(s)
  paintings: 25 ligne(s)
  carts: 2 ligne(s)
  cart_items: 3 ligne(s)
  orders: 5 ligne(s)
  order_items: 8 ligne(s)
  favorites: 2 ligne(s)
  notifications: 1 ligne(s)
  settings: 13 ligne(s)

================================================================================

💾 Rapport complet sauvegardé dans: tenant_migration_report_20240125_103045.json

✅ Migration terminée avec succès
```

## Procédure de Migration

### Prérequis

1. **Base de données configurée**
   ```bash
   # Vérifier que DATABASE_URL ou SUPABASE_DB_URL est définie
   echo $DATABASE_URL
   ```

2. **Table tenants peuplée**
   - Chaque site doit avoir un tenant correspondant dans la table `tenants`
   - Le `host` du tenant doit correspondre au `final_domain` du site

3. **Sauvegarde de la base de données**
   ```bash
   # Créer une sauvegarde avant la migration
   pg_dump $DATABASE_URL > backup_before_tenant_migration_$(date +%Y%m%d).sql
   ```

### Étapes

#### 1. Inspecter l'état actuel

```bash
python inspect_tenant_data.py
```

Vérifier:
- Que tous les tenants nécessaires existent
- Que chaque site a un `final_domain` qui correspond à un `host` dans `tenants`
- L'état actuel des tenant_id (probablement tous à 1)

#### 2. Créer les tenants manquants

Si des sites n'ont pas de tenant correspondant, créer les tenants:

```sql
-- Exemple: créer un tenant pour un nouveau site
INSERT INTO tenants (host, name, created_at)
VALUES ('artist1.artworksdigital.fr', 'Artiste 1', CURRENT_TIMESTAMP);
```

#### 3. Exécuter en mode dry-run

```bash
python migrate_apply_tenant_ids.py --dry-run
```

Vérifier la sortie:
- Aucune erreur
- Tous les sites sont correctement mappés à un tenant
- Les nombres de lignes à mettre à jour sont cohérents
- Aucune ambiguïté détectée

#### 4. Exécuter la migration réelle

```bash
python migrate_apply_tenant_ids.py
```

⚠️ **ATTENTION**: Cette commande modifie la base de données!

#### 5. Vérifier le résultat

```bash
# Inspecter à nouveau
python inspect_tenant_data.py
```

Vérifier:
- Les tenant_id ont été mis à jour correctement
- Aucune donnée n'a le tenant_id = 1 (sauf si c'est voulu)
- Les statistiques par table correspondent aux attentes

#### 6. Consulter le rapport d'audit

```bash
# Le rapport JSON a été généré
cat tenant_migration_report_*.json
```

## Gestion des Erreurs

### Erreur: "Aucun tenant correspondant trouvé"

**Problème**: Un site n'a pas de tenant dans la table `tenants`

**Solution**:
1. Vérifier le `final_domain` du site
2. Créer le tenant manquant avec le bon `host`
3. Relancer la migration

### Erreur: "AMBIGUÏTÉ: Site correspond à plusieurs tenants"

**Problème**: Un domaine correspond à plusieurs entrées dans `tenants`

**Solution**:
1. Identifier les doublons dans la table `tenants`
2. Supprimer ou corriger les entrées en double
3. S'assurer que chaque domaine n'a qu'un seul tenant
4. Relancer la migration

### Avertissement: "tenant_id trouvé est 1 (défaut)"

**Problème**: Le script a trouvé que le tenant_id correct est 1

**Solution**:
- Si c'est voulu (site par défaut), ignorer l'avertissement
- Sinon, vérifier que le tenant a bien été créé avec le bon domaine

### Erreur: "Site n'a pas de user_id"

**Problème**: Un site dans `saas_sites` n'a pas de `user_id`

**Impact**: Les données liées à l'utilisateur ne peuvent pas être mises à jour

**Solution**:
1. Identifier l'utilisateur propriétaire du site
2. Mettre à jour `saas_sites.user_id`
3. Relancer la migration

## Rollback

En cas de problème, restaurer depuis la sauvegarde:

```bash
# Arrêter l'application
# Restaurer la base de données
psql $DATABASE_URL < backup_before_tenant_migration_YYYYMMDD.sql
# Redémarrer l'application
```

## Tests Post-Migration

### 1. Test d'isolation

```bash
# Se connecter avec des utilisateurs de différents tenants
# Vérifier qu'ils ne voient que leurs propres données
```

### 2. Test de fonctionnalité

- Créer une nouvelle peinture
- Ajouter au panier
- Créer une commande
- Vérifier que tout fonctionne normalement

### 3. Test de requêtes

```sql
-- Vérifier qu'aucune donnée n'a tenant_id NULL
SELECT 'users' as table_name, COUNT(*) FROM users WHERE tenant_id IS NULL
UNION ALL
SELECT 'paintings', COUNT(*) FROM paintings WHERE tenant_id IS NULL
UNION ALL
SELECT 'orders', COUNT(*) FROM orders WHERE tenant_id IS NULL;
-- Résultat attendu: 0 pour toutes les tables
```

## Support

En cas de problème:

1. Consulter le fichier `tenant_migration_report_*.json`
2. Vérifier les logs de l'application
3. Restaurer depuis la sauvegarde si nécessaire

## Notes Importantes

- **La migration est idempotente**: On peut la relancer plusieurs fois sans risque
- **Pas de perte de données**: Seul le champ `tenant_id` est modifié
- **Performance**: La migration peut prendre quelques minutes sur une grande base
- **Sécurité**: Toujours tester en dry-run avant la vraie migration
- **Audit**: Le rapport JSON contient tous les détails de la migration

## Architecture

### Stratégie de Mapping

Le script utilise la stratégie suivante pour mapper les sites aux tenants:

1. **Par final_domain**
   - Cherche un tenant où `tenants.host = saas_sites.final_domain`
   - C'est le mapping le plus fiable

2. **Par sandbox_url** (fallback)
   - Si `final_domain` ne correspond pas, essaie avec `sandbox_url`
   - Extrait le domaine de l'URL et cherche dans `tenants.host`

3. **Validation**
   - Si plusieurs tenants correspondent, erreur d'ambiguïté
   - Si aucun tenant ne correspond, avertissement

### Stratégie de Mise à Jour

Pour chaque site identifié:

1. **Mise à jour directe**
   - `saas_sites`: Ligne du site
   - `users`: Utilisateur propriétaire

2. **Mise à jour par user_id**
   - `paintings`: Toutes les peintures de l'utilisateur
   - `carts`: Paniers de l'utilisateur
   - `orders`: Commandes de l'utilisateur
   - `favorites`: Favoris de l'utilisateur
   - `notifications`: Notifications de l'utilisateur
   - `custom_requests`: Demandes de l'utilisateur

3. **Mise à jour par relation**
   - `cart_items`: Items des paniers de l'utilisateur
   - `order_items`: Items des commandes de l'utilisateur

4. **Mise à jour par tenant**
   - `exhibitions`: Toutes les exhibitions du tenant actuel
   - `settings`: Tous les paramètres du tenant actuel
   - `stripe_events`: Tous les événements Stripe du tenant actuel
