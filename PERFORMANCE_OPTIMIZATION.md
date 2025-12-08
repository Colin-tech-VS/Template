# Guide d'Optimisation des Performances

## Problèmes Identifiés et Solutions Appliquées

### 1. Optimisation des Images

#### Problème
- Les images dans `static/Images/` totalisent 15 MB
- Certaines images dépassent 2 MB (ex: biography_20251128_151501.jpg = 2.2 MB)
- Aucun lazy loading n'était appliqué sur les templates

#### Solutions Appliquées
✅ **Lazy Loading ajouté** sur tous les templates :
- `index.html` : Images des dernières créations et boutique
- `galerie.html` : Toutes les images de la galerie
- `boutique.html` : Toutes les images produits

✅ **Image Hero chargée en priorité** (`loading="eager"`) pour l'expérience utilisateur

#### Actions Recommandées (À faire manuellement)
🔧 **Compresser les images** :
```bash
# Utiliser un outil comme imagemagick pour optimiser
mogrify -resize 1200x1200\> -quality 85 static/Images/*.jpg
```

🔧 **Formats modernes** :
- Convertir en WebP pour réduire la taille de 25-35%
- Fournir des fallbacks JPG pour la compatibilité

### 2. Optimisation Base de Données

#### Problème
- Pas d'index sur les colonnes fréquemment requêtées
- Requêtes N+1 sur la page d'accueil (2 requêtes pour le même dataset)
- RANDOM() documenté comme compatible SQLite/PostgreSQL

#### Solutions Appliquées
✅ **Index créés automatiquement** sur :
- `paintings`: category, status, display_order, quantity
- `orders`: user_id, status
- `order_items`: order_id, painting_id
- `cart_items`: cart_id, painting_id
- `carts`: user_id, session_id
- `favorites`: user_id, painting_id

✅ **Optimisation route home** :
- Une seule requête au lieu de deux
- Réutilisation des données en mémoire

✅ **RANDOM() compatible** :
- Fonctionne en SQLite et PostgreSQL
- Documenté dans `database.py`

### 3. Configuration Requise

#### Variables d'Environnement Manquantes

Pour activer toutes les fonctionnalités :

```bash
# Stripe (paiements)
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx

# SMTP (emails)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre-email@gmail.com
SMTP_PASSWORD=votre-mot-de-passe-app

# Dashboard (optionnel)
DASHBOARD_URL=https://admin.artworksdigital.fr
TEMPLATE_MASTER_API_KEY=votre-cle-api

# PostgreSQL Production (optionnel)
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

#### Configuration dans l'interface admin

1. Aller dans `/admin/settings`
2. Configurer :
   - Clés Stripe (si non définies en variables d'environnement)
   - Paramètres SMTP
   - Google Places API Key (pour autocomplete adresse)
   - Couleurs du site
   - Textes personnalisés

### 4. Impact des Optimisations

#### Avant
- Temps de chargement page d'accueil : ~3-5s
- Nombre de requêtes DB : 2+ par page
- Taille totale images : 15 MB non optimisées
- Pas d'index DB : requêtes lentes sur grandes tables

#### Après
- ✅ Lazy loading : images chargées uniquement si visibles
- ✅ Requêtes DB : 1 requête optimisée sur home
- ✅ Index DB : 14 index créés pour accélérer les requêtes
- ✅ Code nettoyé : gestion d'erreur améliorée

#### Gains Estimés
- **Chargement initial** : -50% (avec lazy loading)
- **Requêtes DB** : -30% (avec index)
- **Time to First Paint** : -40% (hero image eager + lazy loading autres)

### 5. Tests de Performance

Pour tester les améliorations :

```bash
# 1. Test local
python app.py

# 2. Vérifier les logs
# Regarder les temps de réponse des routes

# 3. Test avec un outil
# Utiliser Chrome DevTools > Network
# - Vérifier lazy loading fonctionne
# - Temps de chargement des images
# - Nombre de requêtes

# 4. Test PostgreSQL (production)
# Les index sont automatiquement créés au démarrage
```

### 6. Maintenance Continue

#### Checklist Mensuelle
- [ ] Vérifier la taille du dossier `static/Images/`
- [ ] Compresser les nouvelles images ajoutées
- [ ] Vérifier les logs d'erreur
- [ ] Tester les fonctionnalités (paiement, email)

#### Checklist Trimestrielle
- [ ] Analyser les performances avec Google PageSpeed Insights
- [ ] Vérifier les dépendances Python (`pip list --outdated`)
- [ ] Revoir les index DB si nouvelles requêtes fréquentes
- [ ] Backup de la base de données

### 7. Ressources

- [WebP Conversion](https://developers.google.com/speed/webp)
- [Lazy Loading MDN](https://developer.mozilla.org/en-US/docs/Web/Performance/Lazy_loading)
- [PostgreSQL Indexes](https://www.postgresql.org/docs/current/indexes.html)
- [Flask Performance](https://flask.palletsprojects.com/en/2.3.x/deploying/)

---

**Dernière mise à jour**: 2025-12-07
**Version**: 1.0
