# 🔌 API Export - Guide Rapide

## 🚀 Démarrage Rapide

### 1. Récupérer votre clé API

1. Connectez-vous en tant qu'administrateur
2. Allez dans **Admin > API Export**
3. Copiez votre clé API

### 2. Tester l'API

```bash
# Avec cURL (remplacez VOTRE_CLE par votre vraie clé)
curl -H "X-API-Key: VOTRE_CLE" http://127.0.0.1:5000/api/export/stats
```

### 3. Utiliser le script d'exemple

```bash
# Installer requests si nécessaire
pip install requests

# Modifier le script
nano import_data_example.py
# Remplacez "REMPLACEZ_PAR_VOTRE_CLE_API" par votre vraie clé

# Lancer le script
python import_data_example.py
```

---

## 📡 Endpoints Disponibles

| Endpoint | Description | Réponse |
|----------|-------------|---------|
| `/api/export/full` | Toutes les données | JSON complet |
| `/api/export/paintings` | Peintures uniquement | Liste de peintures |
| `/api/export/orders` | Commandes + items | Liste de commandes |
| `/api/export/users` | Utilisateurs | Liste d'utilisateurs |
| `/api/export/exhibitions` | Expositions | Liste d'expositions |
| `/api/export/custom-requests` | Demandes sur mesure | Liste de demandes |
| `/api/export/settings` | Paramètres | Paramètres (clés masquées) |
| `/api/export/stats` | Statistiques | Compteurs et totaux |

---

## 💻 Exemple Python Minimal

```python
import requests

API_KEY = "votre_cle_api"
URL = "http://127.0.0.1:5000/api/export/paintings"

response = requests.get(URL, headers={"X-API-Key": API_KEY})
paintings = response.json()['data']

for painting in paintings:
    print(f"{painting['name']} - {painting['price']} €")
```

---

## 📚 Documentation Complète

- **Documentation détaillée:** `API_EXPORT_DOCUMENTATION.md`
- **Script d'exemple:** `import_data_example.py`
- **Interface web:** http://127.0.0.1:5000/admin/api-export

---

## 🔒 Sécurité

⚠️ **IMPORTANT:**
- Ne committez JAMAIS votre clé API
- Utilisez des variables d'environnement
- Régénérez la clé si compromise
- Utilisez HTTPS en production

---

## ❓ Support

En cas de problème:
1. Vérifiez que le serveur Flask est démarré
2. Vérifiez votre clé API
3. Consultez `API_EXPORT_DOCUMENTATION.md`
4. Testez avec cURL avant d'intégrer

---

**Version:** 1.0  
**Créé le:** 29 novembre 2025
