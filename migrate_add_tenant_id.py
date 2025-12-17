#!/usr/bin/env python3
"""
Migration script to add tenant_id columns to all tables for multi-tenant isolation
This script is idempotent and safe to run multiple times.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Import database functions
from database import get_db_connection, add_column_if_not_exists, execute_query

def migrate_add_tenant_id():
    """Add tenant_id columns to all tables that need them"""
    
    print("="*60)
    print("MIGRATION: Adding tenant_id columns for multi-tenant isolation")
    print("="*60)
    
    # Liste des tables qui nécessitent tenant_id
    tables_needing_tenant_id = [
        'users',
        'paintings',
        'orders',
        'order_items',
        'cart_items',
        'carts',
        'favorites',
        'notifications',
        'exhibitions',
        'custom_requests',
        'settings',
        'stripe_events',
        'saas_sites'
    ]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Créer la table tenants si elle n'existe pas
        print("\n1. Création table 'tenants'...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id SERIAL PRIMARY KEY,
                    host TEXT UNIQUE NOT NULL,
                    name TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("   ✅ Table 'tenants' créée ou vérifiée")
        except Exception as e:
            print(f"   ⚠️  Erreur création table tenants: {e}")
        
        # Insérer le tenant par défaut si nécessaire
        print("\n2. Création tenant par défaut (id=1)...")
        try:
            cursor.execute("SELECT id FROM tenants WHERE id = 1")
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO tenants (id, host, name, created_at)
                    VALUES (1, 'localhost', 'Tenant par défaut', CURRENT_TIMESTAMP)
                """)
                conn.commit()
                print("   ✅ Tenant par défaut créé")
            else:
                print("   ℹ️  Tenant par défaut existe déjà")
        except Exception as e:
            print(f"   ⚠️  Erreur création tenant par défaut: {e}")
        
        # Ajouter tenant_id à chaque table
        print("\n3. Ajout colonne tenant_id aux tables existantes...")
        for table_name in tables_needing_tenant_id:
            try:
                # Vérifier si la table existe
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = %s
                """, (table_name,))
                
                if not cursor.fetchone():
                    print(f"   ℹ️  Table '{table_name}' n'existe pas encore - sera créée au démarrage")
                    continue
                
                # Vérifier si tenant_id existe déjà
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = 'tenant_id'
                """, (table_name,))
                
                if cursor.fetchone():
                    print(f"   ℹ️  Table '{table_name}' a déjà tenant_id")
                else:
                    # Ajouter la colonne avec valeur par défaut
                    cursor.execute(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN tenant_id INTEGER NOT NULL DEFAULT 1
                    """)
                    conn.commit()
                    print(f"   ✅ Colonne tenant_id ajoutée à '{table_name}'")
                    
            except Exception as e:
                print(f"   ⚠️  Erreur table '{table_name}': {e}")
                conn.rollback()
        
        # Créer les indexes pour tenant_id
        print("\n4. Création des indexes de performance pour tenant_id...")
        indexes_to_create = [
            ("idx_users_tenant_id", "users"),
            ("idx_paintings_tenant_id", "paintings"),
            ("idx_orders_tenant_id", "orders"),
            ("idx_order_items_tenant_id", "order_items"),
            ("idx_cart_items_tenant_id", "cart_items"),
            ("idx_carts_tenant_id", "carts"),
            ("idx_favorites_tenant_id", "favorites"),
            ("idx_notifications_tenant_id", "notifications"),
            ("idx_exhibitions_tenant_id", "exhibitions"),
            ("idx_custom_requests_tenant_id", "custom_requests"),
            ("idx_settings_tenant_id", "settings"),
            ("idx_stripe_events_tenant_id", "stripe_events"),
            ("idx_saas_sites_tenant_id", "saas_sites"),
        ]
        
        for index_name, table_name in indexes_to_create:
            try:
                # Vérifier si la table existe
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = %s
                """, (table_name,))
                
                if not cursor.fetchone():
                    continue
                
                # Vérifier si l'index existe déjà
                cursor.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE indexname = %s
                """, (index_name,))
                
                if cursor.fetchone():
                    print(f"   ℹ️  Index '{index_name}' existe déjà")
                else:
                    cursor.execute(f"""
                        CREATE INDEX {index_name} ON {table_name}(tenant_id)
                    """)
                    conn.commit()
                    print(f"   ✅ Index '{index_name}' créé sur {table_name}(tenant_id)")
                    
            except Exception as e:
                print(f"   ⚠️  Erreur index '{index_name}': {e}")
                conn.rollback()
        
        # Créer index composite pour settings (key, tenant_id)
        print("\n5. Création index composite pour settings...")
        try:
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE indexname = 'idx_settings_key_tenant_id'
            """)
            
            if cursor.fetchone():
                print("   ℹ️  Index composite settings existe déjà")
            else:
                # Vérifier si la table existe
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = 'settings'
                """)
                
                if cursor.fetchone():
                    cursor.execute("""
                        CREATE UNIQUE INDEX idx_settings_key_tenant_id 
                        ON settings(key, tenant_id)
                    """)
                    conn.commit()
                    print("   ✅ Index composite créé sur settings(key, tenant_id)")
        except Exception as e:
            print(f"   ⚠️  Erreur index composite settings: {e}")
            conn.rollback()
        
        # Créer index composite pour favorites (user_id, painting_id, tenant_id)
        print("\n6. Création index composite pour favorites...")
        try:
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE indexname = 'idx_favorites_user_painting_tenant'
            """)
            
            if cursor.fetchone():
                print("   ℹ️  Index composite favorites existe déjà")
            else:
                # Vérifier si la table existe
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = 'favorites'
                """)
                
                if cursor.fetchone():
                    cursor.execute("""
                        CREATE UNIQUE INDEX idx_favorites_user_painting_tenant 
                        ON favorites(user_id, painting_id, tenant_id)
                    """)
                    conn.commit()
                    print("   ✅ Index composite créé sur favorites(user_id, painting_id, tenant_id)")
        except Exception as e:
            print(f"   ⚠️  Erreur index composite favorites: {e}")
            conn.rollback()
    
    print("\n" + "="*60)
    print("✅ MIGRATION TERMINÉE")
    print("="*60)
    print("\nNote: Toutes les données existantes ont été associées au tenant_id=1 (défaut)")
    print("Vous pouvez maintenant créer de nouveaux tenants dans la table 'tenants'")
    print("="*60)

if __name__ == "__main__":
    try:
        migrate_add_tenant_id()
    except Exception as e:
        print(f"\n❌ ERREUR MIGRATION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
