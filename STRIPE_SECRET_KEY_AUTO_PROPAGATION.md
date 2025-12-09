# Guide d'Auto-Propagation de la Clé Secrète Stripe

## ⚠️ AVERTISSEMENT DE SÉCURITÉ

La clé secrète Stripe (`sk_test_...` ou `sk_live_...`) est une **credential extrêmement sensible** qui donne un accès complet à votre compte Stripe. Cette documentation explique comment propager cette clé de manière sécurisée du dashboard vers les sites templates.

**Principes de sécurité critiques:**
- ✅ Toujours utiliser HTTPS pour la transmission
- ✅ Ne jamais logger la clé complète (utiliser le masquage)
- ✅ Stocker les clés dans des gestionnaires de secrets (AWS Secrets Manager, Azure Key Vault, etc.)
- ✅ Limiter l'accès aux scripts de propagation aux administrateurs autorisés
- ✅ Utiliser des clés de test (`sk_test_...`) pendant le développement
- ❌ Ne jamais exposer la clé secrète côté client ou dans les logs
- ❌ Ne jamais committer la clé dans Git
- ❌ Ne jamais transmettre la clé par email ou chat non chiffré

## Vue d'ensemble

Le système de propagation permet au dashboard central de pousser automatiquement la clé secrète Stripe vers plusieurs sites templates sans intervention manuelle sur chaque site.

### Architecture

```
Dashboard Central
    ↓ (HTTPS + Auth)
    ↓ PUT /api/export/settings/stripe_secret_key
    ↓ Header: X-API-Key: <TEMPLATE_MASTER_API_KEY>
    ↓ Body: {"value": "sk_test_..."}
    ↓
Template Sites (multiples)
    → Validation de l'authentification
    → Validation du format de la clé
    → Stockage sécurisé dans la base de données
    → Utilisation pour les opérations Stripe côté serveur
```

## Scripts disponibles

### 1. Script synchrone: `dashboard_push_stripe_sk.py`

Script simple et fiable pour pousser la clé secrète vers plusieurs sites séquentiellement.

**Avantages:**
- Facile à déboguer
- Affichage détaillé du statut en temps réel
- Recommandé pour un petit nombre de sites (<10)

**Usage:**

```bash
# Avec arguments en ligne de commande
python dashboard_push_stripe_sk.py \
  --secret-key sk_test_51Hxxx... \
  --master-key template-master-key-2025 \
  --sites-file sites.txt

# Avec variables d'environnement (recommandé)
export STRIPE_SECRET_KEY="sk_test_51Hxxx..."
export TEMPLATE_MASTER_API_KEY="template-master-key-2025"
python dashboard_push_stripe_sk.py --sites-file sites.txt

# Mode dry-run (test sans exécution)
python dashboard_push_stripe_sk.py \
  --secret-key sk_test_51Hxxx... \
  --master-key template-master-key-2025 \
  --sites-file sites.txt \
  --dry-run

# Mode force (sans confirmation interactive)
python dashboard_push_stripe_sk.py \
  --secret-key sk_test_51Hxxx... \
  --master-key template-master-key-2025 \
  --sites-file sites.txt \
  --force
```

### 2. Script asynchrone: `dashboard_push_stripe_sk_async.py`

Version haute performance utilisant asyncio pour pousser vers de nombreux sites en parallèle.

**Avantages:**
- Très rapide pour un grand nombre de sites
- Contrôle de la concurrence
- Recommandé pour >10 sites

**Prérequis:**
```bash
pip install aiohttp
```

**Usage:**

```bash
# Version asynchrone avec concurrence contrôlée
export STRIPE_SECRET_KEY="sk_test_51Hxxx..."
export TEMPLATE_MASTER_API_KEY="template-master-key-2025"
python dashboard_push_stripe_sk_async.py \
  --sites-file sites.txt \
  --concurrency 5

# Dry-run
python dashboard_push_stripe_sk_async.py \
  --sites-file sites.txt \
  --dry-run
```

## Format du fichier sites.txt

```
# Liste des sites templates (une URL par ligne)
# Les lignes commençant par # sont ignorées

https://site1.example.fr
https://site2.example.fr
https://site3.example.fr

# Vous pouvez ajouter des commentaires
https://site4.example.fr
```

## Endpoint API Template

Les sites templates doivent implémenter cet endpoint (déjà présent dans `app.py`):

```python
@app.route('/api/export/settings/stripe_secret_key', methods=['PUT'])
def update_stripe_secret_key():
    """
    Reçoit et stocke la clé secrète Stripe poussée par le dashboard.
    
    Headers requis:
        X-API-Key: <TEMPLATE_MASTER_API_KEY>
    
    Body JSON:
        {"value": "sk_test_..."}
    
    Réponses:
        200: {"success": true, "message": "secret_saved"}
        401: {"success": false, "error": "invalid_api_key"}
        400: {"success": false, "error": "invalid_secret_format"}
    """
    # Validation de l'authentification
    api_key = request.headers.get('X-API-Key')
    if api_key != TEMPLATE_MASTER_API_KEY:
        return jsonify({'success': False, 'error': 'invalid_api_key'}), 401
    
    # Validation du format
    data = request.get_json() or {}
    value = data.get('value')
    if not value or not re.match(r'^sk_(test|live)_[A-Za-z0-9]+$', value):
        return jsonify({'success': False, 'error': 'invalid_secret_format'}), 400
    
    # Stockage sécurisé
    set_setting('stripe_secret_key', value)
    
    return jsonify({'success': True, 'message': 'secret_saved'}), 200
```

## Récupération de la clé secrète sur le template

Le template récupère la clé via la fonction `get_stripe_secret_key()` (déjà implémentée dans `app.py`):

```python
def get_stripe_secret_key():
    """
    Récupère la clé secrète Stripe dans l'ordre de priorité:
    1. Variable d'environnement (STRIPE_SECRET_KEY ou STRIPE_API_KEY)
    2. Base de données locale (settings.stripe_secret_key)
    3. Fallback dashboard (si configuré)
    """
    # 1) Environment variable (highest priority)
    env_key = os.getenv('STRIPE_SECRET_KEY') or os.getenv('STRIPE_API_KEY')
    if env_key:
        return env_key
    
    # 2) Local database
    db_key = get_setting('stripe_secret_key')
    if db_key:
        return db_key
    
    # 3) Dashboard fallback (optional, not recommended for secret keys)
    # ... fallback logic ...
    
    return None
```

## Workflow recommandé

### 1. Configuration initiale

```bash
# Sur le dashboard
export TEMPLATE_MASTER_API_KEY="votre-cle-master-unique-et-forte"
export STRIPE_SECRET_KEY="sk_test_51Hxxx..."

# Créer le fichier sites.txt avec vos sites templates
echo "https://site1.example.fr" > sites.txt
echo "https://site2.example.fr" >> sites.txt
```

### 2. Test avec dry-run

```bash
# Valider la configuration sans modifier les sites
python dashboard_push_stripe_sk.py \
  --sites-file sites.txt \
  --dry-run
```

### 3. Propagation vers les sites de test

```bash
# Pousser vers les sites de test d'abord
# Utiliser une clé de test Stripe
export STRIPE_SECRET_KEY="sk_test_51Hxxx..."
python dashboard_push_stripe_sk.py \
  --sites-file sites-test.txt \
  --force
```

### 4. Vérification

```bash
# Sur chaque site, vérifier que la clé est bien configurée
curl -s https://site1.example.fr/admin/settings | grep -i stripe

# Tester une opération Stripe (création de session checkout, etc.)
```

### 5. Propagation en production

```bash
# Utiliser la clé live uniquement après validation complète
export STRIPE_SECRET_KEY="sk_live_51Hxxx..."
python dashboard_push_stripe_sk.py \
  --sites-file sites-production.txt
  # Vous serez invité à confirmer (pas de --force)
```

## Rotation des clés

Pour effectuer une rotation de la clé secrète Stripe:

1. **Générer une nouvelle clé** dans le Dashboard Stripe
2. **Tester** la nouvelle clé sur un site de staging
3. **Propager** vers tous les sites en utilisant le script
4. **Vérifier** que tous les sites utilisent la nouvelle clé
5. **Révoquer** l'ancienne clé dans le Dashboard Stripe

```bash
# Rotation automatisée
export STRIPE_SECRET_KEY="sk_live_NOUVELLE_CLE..."
python dashboard_push_stripe_sk_async.py \
  --sites-file sites-production.txt \
  --concurrency 10 \
  --force

# Vérifier la propagation
for site in $(cat sites-production.txt); do
  echo "Checking $site..."
  # Test API call or health check
done
```

## Dépannage

### Erreur: "invalid_api_key"

**Cause:** Le `TEMPLATE_MASTER_API_KEY` ne correspond pas sur le site template.

**Solution:**
```bash
# Vérifier la clé sur le dashboard
echo $TEMPLATE_MASTER_API_KEY

# Vérifier la clé sur le template (via admin)
# Ou vérifier le fichier .env du template
```

### Erreur: "invalid_secret_format"

**Cause:** La clé secrète n'est pas au format Stripe valide.

**Solution:**
- Vérifier que la clé commence par `sk_test_` ou `sk_live_`
- Vérifier qu'il n'y a pas d'espaces ou caractères invisibles
- Copier la clé directement depuis le Dashboard Stripe

### Erreur: Timeout

**Cause:** Le site template ne répond pas ou est lent.

**Solution:**
```bash
# Augmenter le timeout dans le script (modifier la valeur par défaut)
# Ou vérifier la santé du site template
curl -I https://site-problematique.example.fr
```

### Erreur: Connection refused

**Cause:** Le site n'est pas accessible ou l'URL est incorrecte.

**Solution:**
- Vérifier que l'URL est correcte et accessible
- Vérifier que le site utilise HTTPS
- Vérifier que le endpoint `/api/export/settings/stripe_secret_key` existe

## Intégration avec CI/CD

### Exemple avec GitHub Actions

```yaml
name: Propagate Stripe Secret Key

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment (test/production)'
        required: true
        default: 'test'

jobs:
  propagate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: pip install requests
      
      - name: Propagate to test sites
        if: github.event.inputs.environment == 'test'
        env:
          STRIPE_SECRET_KEY: ${{ secrets.STRIPE_SECRET_KEY_TEST }}
          TEMPLATE_MASTER_API_KEY: ${{ secrets.TEMPLATE_MASTER_API_KEY }}
        run: |
          python dashboard_push_stripe_sk.py \
            --sites-file sites-test.txt \
            --force
      
      - name: Propagate to production sites
        if: github.event.inputs.environment == 'production'
        env:
          STRIPE_SECRET_KEY: ${{ secrets.STRIPE_SECRET_KEY_LIVE }}
          TEMPLATE_MASTER_API_KEY: ${{ secrets.TEMPLATE_MASTER_API_KEY }}
        run: |
          python dashboard_push_stripe_sk.py \
            --sites-file sites-production.txt \
            --force
```

## Bonnes pratiques

### 1. Séparation test/production

Toujours maintenir des fichiers sites distincts:
- `sites-test.txt` → utiliser `sk_test_...`
- `sites-production.txt` → utiliser `sk_live_...`

### 2. Logs et audit

- Activer les logs côté template pour tracer les mises à jour de clés
- Conserver un historique des propagations
- Masquer toujours les clés dans les logs

### 3. Haute disponibilité

- Propager pendant les heures creuses
- Tester sur un site pilote avant propagation massive
- Avoir un plan de rollback

### 4. Monitoring

- Surveiller les échecs de paiement après propagation
- Mettre en place des alertes sur les erreurs Stripe
- Vérifier régulièrement que les clés sont à jour

## Différences avec la clé publishable

| Aspect | Secret Key (sk_...) | Publishable Key (pk_...) |
|--------|---------------------|--------------------------|
| **Sensibilité** | ⚠️ Très élevée | ✅ Modérée |
| **Usage** | Serveur uniquement | Client (navigateur) |
| **Exposition** | ❌ Jamais | ✅ Peut être publique |
| **Propagation** | Via API sécurisée | Via API ou direct |
| **Stockage** | Env vars + DB chiffrée | DB ou settings |
| **Rotation** | Critique | Simple |

## Support et contact

Pour toute question sur la propagation de la clé secrète:

1. Consulter la documentation Stripe: https://stripe.com/docs/keys
2. Vérifier les logs du template et du dashboard
3. Tester avec le mode dry-run
4. Contacter l'équipe technique si le problème persiste

---

**Dernière mise à jour:** Décembre 2024
**Version:** 1.0
