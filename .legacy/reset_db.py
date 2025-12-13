"""
Script de réinitialisation de la base de données Supabase/PostgreSQL
⚠️  ATTENTION: Ce script supprime TOUTES les données!
"""

import os
import sys

SUPABASE_URL = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')
if not SUPABASE_URL:
    print("❌ Erreur: SUPABASE_DB_URL ou DATABASE_URL non définie")
    print("💡 Définissez-la avec: export SUPABASE_DB_URL='postgresql://...'")
    sys.exit(1)

def reset_database():
    """Réinitialise la base de données Supabase (SUPPRIME TOUT)"""
    from database import get_db  # Returns connection with RealDictCursor
    
    print("🔄 Réinitialisation de la base de données Supabase...")
    print("=" * 70)
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Sauvegarder le compte admin s'il existe
        print("📋 Sauvegarde du compte admin...")
        cursor.execute("SELECT name, email, password, create_date, role FROM users WHERE email = %s", ("coco.cayre@gmail.com",))
        admin_user = cursor.fetchone()
        
        if admin_user:
            # RealDictCursor allows dict-style access
            print(f"   ✅ Admin trouvé: {admin_user['email']}")
        else:
            print("   ⚠️  Aucun admin trouvé")
        
        # Liste des tables à supprimer (ordre inverse des dépendances)
        tables = [
            "order_items", "cart_items", "notifications", 
            "custom_requests", "stripe_events", "saas_sites",
            "orders", "carts", "exhibitions", "paintings", 
            "users", "settings"
        ]
        
        print("\n🗑️  Suppression des tables...")
        for table in tables:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"   ✅ {table} supprimée")
            except Exception as e:
                print(f"   ⚠️  Erreur suppression {table}: {e}")
        
        conn.commit()
        
        # Recréer les tables via init_database()
        print("\n🔧 Recréation des tables...")
        from database import init_database
        init_database()
        
        # Réinsérer le compte admin si sauvegardé
        if admin_user:
            print("\n👤 Restauration du compte admin...")
            cursor.execute("""
                INSERT INTO users (name, email, password, create_date, role) 
                VALUES (%s, %s, %s, %s, %s)
            """, (
                admin_user['name'],
                admin_user['email'], 
                admin_user['password'],
                admin_user['create_date'],
                admin_user['role']
            ))
            conn.commit()
            print(f"   ✅ Admin restauré: {admin_user['email']}")
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ Base de données réinitialisée avec succès!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la réinitialisation: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        conn.close()
        sys.exit(1)


if __name__ == "__main__":
    print("⚠️  " + "=" * 70)
    print("⚠️  ATTENTION: Ce script va SUPPRIMER TOUTES les données!")
    print("⚠️  Cette action est IRRÉVERSIBLE!")
    print("⚠️  " + "=" * 70)
    print()
    
    confirm = input("Tapez 'OUI SUPPRIMER' pour continuer: ")
    if confirm == "OUI SUPPRIMER":
        print()
        reset_database()
    else:
        print("\n✅ Annulé - Aucune modification effectuée")

