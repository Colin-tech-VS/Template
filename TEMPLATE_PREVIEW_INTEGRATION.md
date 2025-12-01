# 🔄 INSTRUCTIONS - Intégration Preview dans le Template

## Objectif
Permettre au template (https://template-vf7p.onrender.com) de recevoir et afficher les données d'un artiste via un paramètre URL `?preview=...`

---

## 📝 Modifications à apporter au Template

### 1. Ajouter un script pour lire les données preview

Ajouter ce code JavaScript dans le template (avant la fermeture du `</body>`):

```javascript
<script>
// Fonction pour lire les paramètres URL
function getPreviewData() {
    const urlParams = new URLSearchParams(window.location.search);
    const previewParam = urlParams.get('preview');
    
    if (previewParam) {
        try {
            // Décoder et parser les données JSON
            const previewData = JSON.parse(decodeURIComponent(previewParam));
            return previewData;
        } catch (e) {
            console.error('Erreur parsing preview data:', e);
            return null;
        }
    }
    return null;
}

// Appliquer les données preview si disponibles
function applyPreviewData() {
    const previewData = getPreviewData();
    
    if (!previewData) {
        return; // Pas de données preview, utiliser les données par défaut
    }
    
    console.log('📦 Données preview reçues:', previewData);
    
    // Afficher une bannière "Mode Preview"
    const previewBanner = document.createElement('div');
    previewBanner.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px; text-align: center; z-index: 10000; font-weight: 600;';
    previewBanner.innerHTML = '🎨 Mode Aperçu - Ceci est une preview de votre boutique';
    document.body.insertBefore(previewBanner, document.body.firstChild);
    
    // Appliquer le nom de la boutique
    if (previewData.shop_name) {
        const shopNameElements = document.querySelectorAll('[data-shop-name], .shop-name, h1.brand-name');
        shopNameElements.forEach(el => {
            el.textContent = previewData.shop_name;
        });
        document.title = `${previewData.shop_name} - Boutique d'Art`;
    }
    
    // Appliquer le style artistique
    if (previewData.art_style) {
        const artStyleElements = document.querySelectorAll('[data-art-style], .art-style, .subtitle');
        artStyleElements.forEach(el => {
            el.textContent = previewData.art_style;
        });
    }
    
    // Appliquer la bio
    if (previewData.bio) {
        const bioElements = document.querySelectorAll('[data-bio], .bio, .description');
        bioElements.forEach(el => {
            el.textContent = previewData.bio;
        });
    }
    
    // Appliquer le logo
    if (previewData.logo_url) {
        const logoElements = document.querySelectorAll('[data-logo], .logo img, .brand-logo');
        logoElements.forEach(el => {
            if (el.tagName === 'IMG') {
                el.src = previewData.logo_url;
            } else {
                el.style.backgroundImage = `url(${previewData.logo_url})`;
            }
        });
    }
    
    // Appliquer les images de la galerie
    if (previewData.images && previewData.images.length > 0) {
        const galleryContainer = document.querySelector('[data-gallery], .gallery, .artworks-grid');
        
        if (galleryContainer) {
            // Vider la galerie existante
            galleryContainer.innerHTML = '';
            
            // Ajouter les nouvelles images
            previewData.images.forEach((imageUrl, index) => {
                const imgElement = document.createElement('div');
                imgElement.className = 'gallery-item';
                imgElement.innerHTML = `
                    <img src="${imageUrl}" 
                         alt="Œuvre ${index + 1}" 
                         loading="lazy"
                         style="width: 100%; height: 100%; object-fit: cover; border-radius: 8px;">
                `;
                galleryContainer.appendChild(imgElement);
            });
        }
    }
    
    // Appliquer l'email
    if (previewData.email) {
        const emailElements = document.querySelectorAll('[data-email], a[href^="mailto:"]');
        emailElements.forEach(el => {
            if (el.tagName === 'A') {
                el.href = `mailto:${previewData.email}`;
            }
            el.textContent = previewData.email;
        });
    }
    
    // Appliquer le téléphone
    if (previewData.phone) {
        const phoneElements = document.querySelectorAll('[data-phone], .contact-phone');
        phoneElements.forEach(el => {
            el.textContent = previewData.phone;
        });
    }
    
    // Appliquer Instagram
    if (previewData.instagram) {
        const instagramElements = document.querySelectorAll('[data-instagram], .instagram-link');
        instagramElements.forEach(el => {
            const username = previewData.instagram.replace('@', '');
            if (el.tagName === 'A') {
                el.href = `https://instagram.com/${username}`;
            }
            el.textContent = `@${username}`;
        });
    }
}

// Exécuter au chargement de la page
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyPreviewData);
} else {
    applyPreviewData();
}
</script>
```

---

## 2. Ajouter des attributs data-* aux éléments modifiables

Pour que le script fonctionne mieux, ajoutez ces attributs aux éléments HTML:

```html
<!-- Nom de la boutique -->
<h1 data-shop-name class="brand-name">Nom par défaut</h1>

<!-- Style artistique -->
<p data-art-style class="subtitle">Style par défaut</p>

<!-- Bio -->
<div data-bio class="description">Bio par défaut</div>

<!-- Logo -->
<img data-logo src="logo-default.jpg" alt="Logo">

<!-- Galerie -->
<div data-gallery class="artworks-grid">
    <!-- Les images seront injectées ici -->
</div>

<!-- Email -->
<a data-email href="mailto:contact@example.com">contact@example.com</a>

<!-- Téléphone -->
<span data-phone class="contact-phone">+33 X XX XX XX XX</span>

<!-- Instagram -->
<a data-instagram href="https://instagram.com/username">@username</a>
```

---

## 3. Test du système

### URL de test:
```
https://template-vf7p.onrender.com/?preview=%7B%22shop_name%22%3A%22Galerie%20Martin%22%2C%22art_style%22%3A%22Peinture%20Abstraite%22%2C%22bio%22%3A%22Artiste%20parisien%20sp%C3%A9cialis%C3%A9%20dans%20l'art%20abstrait%22%2C%22logo_url%22%3A%22https%3A%2F%2Fexample.com%2Flogo.jpg%22%2C%22images%22%3A%5B%22https%3A%2F%2Fexample.com%2F1.jpg%22%2C%22https%3A%2F%2Fexample.com%2F2.jpg%22%5D%7D
```

### Générer une URL de test:
```javascript
const testData = {
    shop_name: "Galerie Martin",
    art_style: "Peinture Abstraite",
    bio: "Artiste parisien spécialisé dans l'art abstrait",
    logo_url: "https://example.com/logo.jpg",
    images: ["https://example.com/1.jpg", "https://example.com/2.jpg"]
};

const url = `https://template-vf7p.onrender.com/?preview=${encodeURIComponent(JSON.stringify(testData))}`;
console.log(url);
```

---

## 4. Vérification

Après implémentation, vérifiez que:
- ✅ La bannière "Mode Aperçu" s'affiche
- ✅ Le nom de la boutique est remplacé
- ✅ Les images de la galerie sont remplacées
- ✅ Le logo est remplacé
- ✅ La bio est affichée
- ✅ Les informations de contact sont mises à jour

---

## 🚀 Déploiement

1. Appliquez ces modifications au template sur Render
2. Testez avec l'URL générée depuis Artworks_Digital
3. Les artistes pourront voir leur preview immédiatement après soumission du formulaire!

