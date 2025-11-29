# Standards de Design - Site JB Artiste Peintre

## 📐 Grilles et Layout

### Grilles de produits (Index, Boutique, About, Profile, Expositions)
```css
display: grid;
grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
gap: 25px;
```

### Galerie Instagram (page galerie uniquement)
```css
display: grid;
grid-template-columns: repeat(4, 1fr);
gap: 1px;
```

## 🎨 Cartes Produit

### Style de base
```css
background: #ffffff;
border-radius: 12px;
box-shadow: 0 8px 20px rgba(0,0,0,0.08);
transition: all 0.3s ease;
```

### Effet hover
```css
transform: translateY(-4px) scale(1.02);
box-shadow: 0 12px 28px rgba(0,0,0,0.12);
```

### Images
```css
height: 250px;
object-fit: cover;
transition: transform 0.3s ease;
```

### Hover sur images
```css
transform: scale(1.08);
```

## ❤️ Boutons Favoris

### Style standard
```css
position: absolute;
top: 10px;
right: 10px;
font-size: 22px;
background: rgba(255,255,255,0.9);
border-radius: 50%;
width: 40px;
height: 40px;
display: flex;
align-items: center;
justify-content: center;
text-decoration: none;
transition: all 0.3s ease;
```

### Hover
```css
background: rgba(255,255,255,1);
transform: scale(1.1);
```

## 🏷️ Badges de Statut

### Style standard
```css
position: absolute;
top: 10px;
left: 10px;
padding: 6px 12px;
font-size: 13px;
font-weight: 600;
border-radius: 6px;
```

## 📝 Typographie

### Titres de section (h1)
```css
font-size: 36px;
color: #1E3A8A;
font-weight: 700;
margin-bottom: 20px;
```

### Titres de section (h2)
```css
font-size: 32px;
color: #1E3A8A;
font-weight: 700;
text-align: center;
margin-bottom: 40px;
```

## 📏 Espacements

### Gap pour grilles de produits
```css
gap: 25px;
```

### Gap pour sections majeures
```css
gap: 30px;
```

### Padding sections
```css
padding: 60px 20px;
```

## 🎨 Couleurs Principales

- Primary: `#1E3A8A` (bleu foncé)
- Secondary: `#3B65C4` (bleu moyen)
- Gradient: `linear-gradient(90deg, #1E3A8A, #3B65C4)`
- Text: `#1a1a1a` / `#333`
- Text Light: `#666` / `#555`
- Background: `linear-gradient(to bottom, #e0f2ff, #c0d9ff)`

## 📱 Responsive

### Grilles mobiles
```css
@media (max-width: 768px) {
    grid-template-columns: 1fr;
}
```

### Galerie mobile (4 colonnes conservées)
```css
@media (max-width: 768px) {
    grid-template-columns: repeat(4, 1fr);
}
```

## ✅ Pages Standardisées

- ✅ index.html
- ✅ boutique.html
- ✅ galerie.html (style Instagram préservé)
- ✅ about.html
- ✅ profile.html
- ✅ cart.html
- ✅ checkout.html
- ✅ contact.html
- ✅ order.html
- ✅ painting_detail.html
- ✅ expositions.html
- ✅ custom_orders.html
- ✅ style.css (global)

## 🔄 Transitions Standardisées

### Cartes
```css
transition: all 0.3s ease;
```

### Images
```css
transition: transform 0.3s ease;
```

### Boutons
```css
transition: all 0.3s ease;
```

---

**Dernière mise à jour:** 29 novembre 2025  
**Objectif:** Cohérence visuelle totale sur tout le site
