# Instructions de vérification manuelle

## Avant de merger cette PR, effectuer les tests suivants :

### 1. Tests locaux (développement)

#### Installation et configuration
```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Copier .env.example vers .env
cp .env.example .env

# 3. Éditer .env et définir :
#    - TEMPLATE_MASTER_API_KEY (requis)
#    - FLASK_SECRET (requis)
#    - MAIL_USERNAME et MAIL_PASSWORD (optionnel pour tests email)

# 4. Lancer l'application
python app.py
```

#### Vérifications au démarrage

Observer les logs au démarrage et confirmer :

```
✅ Attendu : "🔐 Flask secret_key configurée depuis l'environnement"
❌ Si vous voyez : "⚠️  Flask secret_key générée aléatoirement" 
   → Définissez FLASK_SECRET dans .env

✅ Attendu : "📧 SMTP configuré: smtp.gmail.com:587 (user: ✓, pass: ✓)"
   OU : "📧 SMTP configuré: smtp.gmail.com:587 (user: ✗, pass: ✗)"
   (selon si MAIL_USERNAME/MAIL_PASSWORD sont définis)

✅ Attendu : "🔑 Clé maître dashboard chargée: template-..."
✅ Attendu : "✅ Administrateur configuré: admin@example.com"
```

#### Tests des endpoints API

Dans un autre terminal :

```bash
# Définir la clé API
export MASTER_KEY="votre-valeur-TEMPLATE_MASTER_API_KEY"
export BASE_URL="http://localhost:5000"

# Test 1: Stats
curl -H "X-API-Key: $MASTER_KEY" $BASE_URL/api/export/stats | jq .
# Attendu: JSON avec statistiques

# Test 2: Orders avec pagination
curl -H "X-API-Key: $MASTER_KEY" "$BASE_URL/api/export/orders?page=1&per_page=5" | jq .
# Attendu: JSON avec 'orders' et 'pagination'
# Vérifier que chaque order a :
#   - id, customer_name, email, total_price, order_date, status
#   - items (array avec painting_id, name, image, price, quantity)
#   - site_name

# Test 3: Stripe PK (public endpoint, pas d'auth)
curl $BASE_URL/api/stripe-pk | jq .
# Attendu: 404 si pas configuré OU 200 avec publishable_key

# Test 4: Test sans API key (doit échouer)
curl $BASE_URL/api/export/orders
# Attendu: {"error": "API key manquante"}

# Test 5: Test avec mauvaise API key (doit échouer)
curl -H "X-API-Key: bad-key" $BASE_URL/api/export/orders
# Attendu: {"error": "API key invalide"}
```

### 2. Vérifications de sécurité

#### A. Aucun credential en dur
```bash
# Ces commandes doivent toutes afficher "Passed" ou ne rien trouver
cd /chemin/vers/Template

# Vérifier emails
grep -r "coco.cayre@" app.py && echo "❌ Email trouvé" || echo "✅ Passed"

# Vérifier mots de passe
grep -r "motdepassepardefaut" app.py && echo "❌ Password trouvé" || echo "✅ Passed"
grep -r "psgk wjhd" app.py && echo "❌ Gmail token trouvé" || echo "✅ Passed"

# Vérifier secret_key
grep "secret_key = 'secret_key'" app.py && echo "❌ Secret key trouvée" || echo "✅ Passed"
```

#### B. Validation des clés Stripe

Si vous avez configuré des clés Stripe dans settings :

```bash
# Essayer de récupérer la clé publishable
curl http://localhost:5000/api/stripe-pk

# Vérifier dans les logs qu'aucun message [SECURITY] n'apparaît
# Si une clé sk_ ou rk_ était retournée, un log [SECURITY] apparaîtrait
```

### 3. Tests fonctionnels

#### A. Mode Preview

Accéder à l'application avec différents paramètres :

```bash
# Test 1: Sans preview
curl -s http://localhost:5000/ | grep -i "preview" || echo "Mode normal"

# Test 2: Avec preview=true
curl -s "http://localhost:5000/?preview=true" | head -5

# Test 3: Avec preview=1
curl -s "http://localhost:5000/?preview=1" | head -5

# Vérifier les logs pour :
# "[DEBUG] is_preview_request - Mode preview détecté"
```

#### B. Fetch prix dashboard

Observer les logs pour ces lignes (si dashboard configuré) :

```
[DEBUG] fetch_dashboard_site_price - base_url: ..., site_id: ...
[DEBUG] fetch_dashboard_site_price - Tentative endpoint: ...
[DEBUG] fetch_dashboard_site_price - Prix trouvé dans champ 'price': ...
```

### 4. Tests d'intégration avec Dashboard

Si vous avez accès au dashboard central :

#### A. Pousser une configuration depuis le dashboard

```bash
# Exemple: Mettre à jour le nom du site
curl -X PUT \
  -H "X-API-Key: $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value": "Mon Nouveau Site"}' \
  http://localhost:5000/api/export/settings/site_name

# Vérifier
curl -H "X-API-Key: $MASTER_KEY" \
  http://localhost:5000/api/export/settings | jq '.data[] | select(.key=="site_name")'
```

#### B. Récupérer les données depuis le dashboard

Depuis le dashboard, tester l'import des données :

```bash
# Sur la machine du dashboard
curl -H "X-API-Key: TEMPLATE_MASTER_API_KEY_VALUE" \
  https://template-url/api/export/orders?page=1&per_page=10
```

### 5. Tests de performance (optionnel)

#### Test de pagination sur gros volumes

Si vous avez beaucoup de commandes :

```bash
# Récupérer 500 commandes (max par page)
time curl -s -H "X-API-Key: $MASTER_KEY" \
  "$BASE_URL/api/export/orders?page=1&per_page=500" > /dev/null

# Vérifier que la réponse est rapide (< 5 secondes recommandé)
```

### 6. Checklist finale avant merge

- [ ] Tous les tests API passent
- [ ] Aucune alerte de sécurité (grep pour credentials)
- [ ] Les logs de démarrage sont corrects
- [ ] Le mode preview fonctionne
- [ ] La pagination fonctionne
- [ ] Les clés Stripe sont protégées
- [ ] L'authentification API fonctionne
- [ ] La documentation est à jour
- [ ] Le fichier .env est dans .gitignore
- [ ] Les variables d'environnement sont documentées

### 7. Déploiement en production (après merge)

#### Étapes recommandées :

1. **Préparer les variables d'environnement production**
   ```bash
   # Sur Render, Scalingo, ou votre plateforme
   TEMPLATE_MASTER_API_KEY=<générer avec secrets.token_urlsafe(32)>
   FLASK_SECRET=<générer avec secrets.token_urlsafe(32)>
   MAIL_USERNAME=<votre email SMTP>
   MAIL_PASSWORD=<mot de passe d'application>
   ADMIN_EMAIL=<email admin principal>
   ```

2. **Déployer la nouvelle version**

3. **Vérifier les logs au démarrage**
   - Chercher les messages 🔐, 📧, 🔑, ✅

4. **Tester les endpoints en production**
   ```bash
   export PROD_URL="https://votre-template.artworksdigital.fr"
   export MASTER_KEY="votre-cle-production"
   
   # Test rapide
   curl -H "X-API-Key: $MASTER_KEY" $PROD_URL/api/export/stats
   ```

5. **Tester l'intégration dashboard → template**

6. **Monitorer les logs pendant 24h**
   - Vérifier qu'aucune erreur liée aux variables d'environnement
   - Vérifier que l'authentification API fonctionne

### 8. Rollback si nécessaire

En cas de problème en production :

1. **Revenir à la version précédente**
   ```bash
   git revert HEAD
   git push
   ```

2. **OU** définir les anciennes valeurs en environnement temporairement
   (non recommandé, mais possible en urgence)

3. **Identifier et corriger le problème**

4. **Re-déployer**

---

## 🆘 Support

Si vous rencontrez des problèmes :

1. **Vérifier les logs** au démarrage de l'application
2. **Consulter TESTING_GUIDE.md** pour des exemples détaillés
3. **Consulter PR_SUMMARY.md** pour comprendre les changements
4. **Vérifier que .env contient les bonnes valeurs**
5. **Tester en local avant la production**

## 📝 Notes importantes

- ⚠️  **Ne jamais commiter le fichier .env**
- ⚠️  **Utiliser des mots de passe d'application Gmail** (pas le mot de passe principal)
- ⚠️  **Générer des clés secrètes fortes** en production
- ⚠️  **Tester en local d'abord**, puis en staging, puis en production
- ✅  **Les fallbacks assurent la rétrocompatibilité** mais sont moins sécurisés

---

**Cette PR est prête à être mergée une fois les tests manuels effectués et validés.**
