# 🚀 Déploiement Scalingo - Guide Rapide

## ✅ Checklist de déploiement

### 1️⃣ Ajouter la variable d'environnement sur Scalingo

Dans l'interface web de votre app **template.artworksdigital.fr** :

```
Dashboard Scalingo > Mon App > Environment > Environment variables
```

**Ajouter cette variable :**
```
TEMPLATE_MASTER_API_KEY=template-master-key-2025
```

> 💡 L'app redémarrera automatiquement après avoir sauvegardé

---

### 2️⃣ Vérifier le code (déjà fait ✅)

Le code a été modifié pour :
- ✅ Charger `TEMPLATE_MASTER_API_KEY` depuis l'environnement
- ✅ Route `/api/export/settings/<key>` accepte la clé maître
- ✅ Logs détaillés pour déboguer
- ✅ INSERT automatique si le paramètre n'existe pas

---

### 3️⃣ Déployer sur Scalingo

```bash
# S'assurer d'être sur main
git checkout main

# Ajouter les modifications
git add .

# Commit
git commit -m "Add TEMPLATE_MASTER_API_KEY for dashboard integration"

# Push vers Scalingo (adapter 'scalingo' au nom de votre remote)
git push scalingo main

# OU si vous utilisez origin
git push origin main
# Puis attendre le déploiement automatique Scalingo
```

---

### 4️⃣ Vérifier dans les logs Scalingo

Après le redémarrage, vous devriez voir ce log au démarrage :
```
🔑 Clé maître dashboard chargée: template-ma...y-2025
```

Pour voir les logs en temps réel :
```bash
scalingo --app template logs -f
```

---

### 5️⃣ Tester l'API

#### Test depuis le terminal local :

```bash
curl -X PUT https://template.artworksdigital.fr/api/export/settings/test_key \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value": "test_value"}'
```

**Résultat attendu :**
```json
{"success": true, "message": "Paramètre test_key mis à jour"}
```

#### Test du prix SAAS :

```bash
curl -X PUT https://template.artworksdigital.fr/api/export/settings/saas_site_price_cache \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value": "550.00"}'
```

---

### 6️⃣ Vérifier dans les logs Scalingo

Vous devriez voir ces logs lors de l'appel API :
```
[API] 🔑 Clé maître acceptée - Configuration saas_site_price_cache
[API] ✅ Paramètre 'saas_site_price_cache' mis à jour: 550.00
```

---

## 🐛 Dépannage

### La clé ne fonctionne pas ?

1. **Vérifier que la variable est bien définie :**
   ```bash
   scalingo --app template env | grep TEMPLATE_MASTER_API_KEY
   ```
   Devrait afficher : `TEMPLATE_MASTER_API_KEY=template-master-key-2025`

2. **Redémarrer manuellement l'app :**
   ```bash
   scalingo --app template restart
   ```

3. **Vérifier les logs au démarrage :**
   ```bash
   scalingo --app template logs --lines 50 | grep "Clé maître"
   ```

### Erreur 403 "Clé API invalide" ?

Vérifiez le header HTTP :
```bash
# ✅ Bon
-H "X-API-Key: template-master-key-2025"

# ❌ Erreurs courantes
-H "Authorization: Bearer template-master-key-2025"  # Mauvais header
-H "API-Key: template-master-key-2025"              # Manque le X-
-H "X-API-Key: template-master-key-2024"            # Mauvaise année
```

### Erreur 500 ?

Vérifiez les logs d'erreur :
```bash
scalingo --app template logs -f
```

Recherchez les lignes avec `[API] ❌`

---

## 🎉 Une fois que tout fonctionne

Le **dashboard** peut maintenant :
1. Créer un site preview sur un sous-domaine
2. Appeler l'API du template pour configurer le prix : `PUT /api/export/settings/saas_site_price_cache`
3. Le prix s'affiche automatiquement sur le bouton "Lancer mon site" en bas à gauche

---

## 📞 Support

Si vous rencontrez un problème :
1. Vérifiez les logs Scalingo : `scalingo --app template logs -f`
2. Testez avec cURL pour isoler le problème
3. Vérifiez que la variable d'environnement est bien définie

---

## 🔒 Sécurité

⚠️ **Important :**
- Ne commitez JAMAIS la clé dans le code
- Utilisez toujours HTTPS en production
- Changez la clé si elle est compromise
- Loggez tous les accès API pour audit

✅ **Bon :**
- Variable d'environnement Scalingo
- Fichier `.env` local (dans `.gitignore`)
- Logs de toutes les modifications

❌ **Mauvais :**
- Clé en dur dans le code : `api_key = "template-master-key-2025"`
- Clé dans un fichier commité sur Git
- Pas de logs des modifications
