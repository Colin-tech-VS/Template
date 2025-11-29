"""
Script d'exemple pour importer les données du site JB Artiste Peintre
dans un nouveau site ou une application externe.

Usage:
    python import_data_example.py

Configuration:
    Modifiez les variables API_KEY et SOURCE_URL ci-dessous
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Any

# ================================
# CONFIGURATION
# ================================

# Votre clé API (récupérée depuis Admin > API Export)
API_KEY = "REMPLACEZ_PAR_VOTRE_CLE_API"

# URL du site source
SOURCE_URL = "http://127.0.0.1:5000"  # Changez en production

# Headers pour l'authentification
HEADERS = {
    "X-API-Key": API_KEY
}

# ================================
# FONCTIONS D'EXPORT
# ================================

def export_full_data() -> Dict[str, Any]:
    """Exporte TOUTES les données du site"""
    print("📦 Export complet des données...")
    
    response = requests.get(
        f"{SOURCE_URL}/api/export/full",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['total_records']} enregistrements exportés depuis {data['tables_count']} tables")
        return data
    elif response.status_code == 401:
        print("❌ Erreur 401: Clé API manquante")
        return None
    elif response.status_code == 403:
        print("❌ Erreur 403: Clé API invalide")
        return None
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
        return None


def export_paintings() -> List[Dict[str, Any]]:
    """Exporte uniquement les peintures"""
    print("🖼️  Export des peintures...")
    
    response = requests.get(
        f"{SOURCE_URL}/api/export/paintings",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['count']} peintures exportées")
        return data['data']
    else:
        print(f"❌ Erreur {response.status_code}")
        return []


def export_orders() -> List[Dict[str, Any]]:
    """Exporte les commandes avec leurs items"""
    print("📦 Export des commandes...")
    
    response = requests.get(
        f"{SOURCE_URL}/api/export/orders",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['count']} commandes exportées")
        return data['data']
    else:
        print(f"❌ Erreur {response.status_code}")
        return []


def export_stats() -> Dict[str, Any]:
    """Exporte des statistiques générales"""
    print("📊 Export des statistiques...")
    
    response = requests.get(
        f"{SOURCE_URL}/api/export/stats",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Statistiques exportées:")
        for key, value in data['stats'].items():
            print(f"   - {key}: {value}")
        return data['stats']
    else:
        print(f"❌ Erreur {response.status_code}")
        return {}


# ================================
# FONCTIONS D'IMPORT (EXEMPLE)
# ================================

def import_paintings_to_new_site(paintings: List[Dict[str, Any]]):
    """
    Exemple d'import des peintures dans un nouveau site
    Adaptez cette fonction selon votre architecture
    """
    print("\n🔄 Import des peintures dans le nouveau site...")
    
    for painting in paintings:
        try:
            # EXEMPLE: Adapter selon votre BDD/API
            # Si vous utilisez Flask avec SQLAlchemy:
            # new_painting = Painting(
            #     name=painting['name'],
            #     price=painting['price'],
            #     image=painting['image'],
            #     ...
            # )
            # db.session.add(new_painting)
            
            # Si vous utilisez une API REST:
            # response = requests.post(
            #     "http://nouveau-site.com/api/paintings",
            #     json=painting
            # )
            
            print(f"   ✅ Importé: {painting['name']} ({painting['price']} €)")
            
        except Exception as e:
            print(f"   ❌ Erreur pour {painting['name']}: {e}")
    
    # db.session.commit()  # Si SQLAlchemy
    print(f"\n✅ {len(paintings)} peintures importées")


def save_to_json(data: Any, filename: str):
    """Sauvegarde les données dans un fichier JSON"""
    print(f"\n💾 Sauvegarde dans {filename}...")
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Données sauvegardées dans {filename}")


# ================================
# SCRIPT PRINCIPAL
# ================================

def main():
    """Fonction principale"""
    print("=" * 60)
    print("🎨 IMPORT DE DONNÉES - JB ARTISTE PEINTRE")
    print("=" * 60)
    print()
    
    # Vérifier la configuration
    if API_KEY == "REMPLACEZ_PAR_VOTRE_CLE_API":
        print("❌ ERREUR: Vous devez configurer votre clé API !")
        print("   1. Allez sur http://127.0.0.1:5000/admin/api-export")
        print("   2. Copiez votre clé API")
        print("   3. Remplacez 'REMPLACEZ_PAR_VOTRE_CLE_API' dans ce script")
        return
    
    print(f"🔗 Source: {SOURCE_URL}")
    print(f"🔑 Clé API: {API_KEY[:10]}...{API_KEY[-10:]}")
    print()
    
    # Menu interactif
    print("Que voulez-vous faire ?")
    print("1. Exporter TOUTES les données")
    print("2. Exporter uniquement les peintures")
    print("3. Exporter uniquement les commandes")
    print("4. Afficher les statistiques")
    print("5. Tout exporter et sauvegarder en JSON")
    print()
    
    choice = input("Votre choix (1-5): ").strip()
    
    if choice == "1":
        # Export complet
        data = export_full_data()
        if data:
            print("\n📋 Résumé:")
            for table, records in data['data'].items():
                print(f"   - {table}: {len(records)} enregistrements")
            
            save = input("\n💾 Sauvegarder dans un fichier JSON ? (o/n): ").strip().lower()
            if save == 'o':
                filename = f"export_complet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                save_to_json(data, filename)
    
    elif choice == "2":
        # Export peintures
        paintings = export_paintings()
        if paintings:
            print(f"\n📋 {len(paintings)} peintures trouvées")
            
            # Afficher les 3 premières
            print("\n🖼️  Aperçu des 3 premières peintures:")
            for i, painting in enumerate(paintings[:3], 1):
                print(f"   {i}. {painting['name']} - {painting['price']} €")
                print(f"      Catégorie: {painting.get('category', 'N/A')}")
                print(f"      Stock: {painting.get('quantity', 0)} unités")
            
            save = input("\n💾 Sauvegarder dans un fichier JSON ? (o/n): ").strip().lower()
            if save == 'o':
                filename = f"paintings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                save_to_json(paintings, filename)
            
            # Option d'import (exemple)
            # import_choice = input("\n🔄 Importer dans le nouveau site ? (o/n): ").strip().lower()
            # if import_choice == 'o':
            #     import_paintings_to_new_site(paintings)
    
    elif choice == "3":
        # Export commandes
        orders = export_orders()
        if orders:
            print(f"\n📋 {len(orders)} commandes trouvées")
            
            # Calculer le chiffre d'affaires total
            total_revenue = sum(order['total_price'] for order in orders)
            print(f"\n💰 Chiffre d'affaires total: {total_revenue:.2f} €")
            
            # Afficher les 3 dernières commandes
            print("\n📦 Dernières commandes:")
            for i, order in enumerate(orders[:3], 1):
                print(f"   {i}. #{order['id']} - {order['customer_name']}")
                print(f"      Total: {order['total_price']} €")
                print(f"      Date: {order['order_date']}")
                print(f"      Items: {len(order['items'])} produit(s)")
            
            save = input("\n💾 Sauvegarder dans un fichier JSON ? (o/n): ").strip().lower()
            if save == 'o':
                filename = f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                save_to_json(orders, filename)
    
    elif choice == "4":
        # Statistiques
        stats = export_stats()
        
        if stats:
            print("\n📊 STATISTIQUES DU SITE")
            print("=" * 40)
            print(f"Peintures: {stats.get('paintings_count', 0)}")
            print(f"Commandes: {stats.get('orders_count', 0)}")
            print(f"Utilisateurs: {stats.get('users_count', 0)}")
            print(f"Expositions: {stats.get('exhibitions_count', 0)}")
            print(f"Revenu total: {stats.get('total_revenue', 0):.2f} €")
            print(f"Commandes livrées: {stats.get('delivered_orders', 0)}")
    
    elif choice == "5":
        # Tout exporter
        data = export_full_data()
        if data:
            filename = f"export_complet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            save_to_json(data, filename)
            
            print("\n✅ Export terminé !")
            print(f"📁 Fichier: {filename}")
            print(f"📊 Tables exportées: {data['tables_count']}")
            print(f"📝 Total d'enregistrements: {data['total_records']}")
    
    else:
        print("❌ Choix invalide")
    
    print("\n" + "=" * 60)
    print("✅ Script terminé")
    print("=" * 60)


# ================================
# POINT D'ENTRÉE
# ================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Script interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
