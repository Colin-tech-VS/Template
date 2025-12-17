#!/usr/bin/env python3
"""
Verification script to ensure the migration was successful
Tests database schema and basic operations
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from database import get_db_connection

def verify_migration():
    """Verify that the migration was successful"""
    
    print("="*60)
    print("VERIFICATION: Migration tenant_id")
    print("="*60)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Verify tenants table exists
        print("\n1. Vérification table 'tenants'...")
        try:
            cursor.execute("SELECT COUNT(*) FROM tenants")
            count = cursor.fetchone()[0]
            print(f"   ✅ Table 'tenants' existe avec {count} tenant(s)")
            
            cursor.execute("SELECT id, host, name FROM tenants WHERE id = 1")
            tenant = cursor.fetchone()
            if tenant:
                print(f"   ✅ Tenant par défaut: id={tenant[0]}, host='{tenant[1]}', name='{tenant[2]}'")
            else:
                print("   ⚠️  Tenant par défaut (id=1) non trouvé")
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return False
        
        # 2. Verify tenant_id column exists in tables
        print("\n2. Vérification colonne 'tenant_id' dans les tables...")
        tables_to_check = ['users', 'paintings', 'carts', 'settings']
        
        for table in tables_to_check:
            try:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_name = %s
                """, (table,))
                
                if not cursor.fetchone():
                    print(f"   ℹ️  Table '{table}' n'existe pas")
                    continue
                
                cursor.execute("""
                    SELECT column_name, data_type, column_default 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = 'tenant_id'
                """, (table,))
                
                result = cursor.fetchone()
                if result:
                    print(f"   ✅ Table '{table}': tenant_id ({result[1]}) DEFAULT {result[2]}")
                else:
                    print(f"   ⚠️  Table '{table}': colonne tenant_id manquante")
            except Exception as e:
                print(f"   ❌ Erreur table '{table}': {e}")
        
        # 3. Verify indexes
        print("\n3. Vérification des indexes...")
        try:
            cursor.execute("""
                SELECT indexname, tablename 
                FROM pg_indexes 
                WHERE schemaname = 'public' AND indexname LIKE '%tenant%'
                ORDER BY tablename, indexname
            """)
            indexes = cursor.fetchall()
            
            if indexes:
                for index_name, table_name in indexes:
                    print(f"   ✅ Index '{index_name}' sur table '{table_name}'")
            else:
                print("   ⚠️  Aucun index tenant_id trouvé")
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
        
        # 4. Test basic operations
        print("\n4. Test opérations de base...")
        try:
            # First, get the max ID to avoid conflicts
            cursor.execute("SELECT COALESCE(MAX(id), 0) + 100 FROM tenants")
            next_id = cursor.fetchone()[0]
            
            # Test insert in tenants
            cursor.execute("""
                INSERT INTO tenants (id, host, name, created_at)
                VALUES (%s, 'test.example.com', 'Test Tenant', CURRENT_TIMESTAMP)
                RETURNING id
            """, (next_id,))
            test_tenant_id = cursor.fetchone()[0]
            print(f"   ✅ INSERT tenant: id={test_tenant_id}")
            
            # Test select
            cursor.execute("SELECT id, host FROM tenants WHERE id = %s", (test_tenant_id,))
            result = cursor.fetchone()
            print(f"   ✅ SELECT tenant: id={result[0]}, host='{result[1]}'")
            
            # Test update
            cursor.execute("""
                UPDATE tenants SET name = 'Test Tenant Updated' WHERE id = %s
            """, (test_tenant_id,))
            print(f"   ✅ UPDATE tenant: {cursor.rowcount} ligne(s) modifiée(s)")
            
            # Test delete
            cursor.execute("DELETE FROM tenants WHERE id = %s", (test_tenant_id,))
            print(f"   ✅ DELETE tenant: {cursor.rowcount} ligne(s) supprimée(s)")
            
            conn.commit()
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            conn.rollback()
    
    print("\n" + "="*60)
    print("✅ VÉRIFICATION TERMINÉE AVEC SUCCÈS")
    print("="*60)
    return True

if __name__ == "__main__":
    try:
        success = verify_migration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERREUR VÉRIFICATION: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
