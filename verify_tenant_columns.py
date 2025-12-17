#!/usr/bin/env python3
"""
Script to verify which tables have tenant_id column in the actual database
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Check DATABASE_URL is set
DATABASE_URL = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Error: SUPABASE_DB_URL or DATABASE_URL not defined")
    sys.exit(1)

try:
    from database import get_db_connection
    
    print("=" * 70)
    print("🔍 VERIFICATION: Tables with tenant_id column")
    print("=" * 70)
    
    # Liste des tables qui devraient avoir tenant_id selon le code
    expected_tables_with_tenant_id = [
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
        
        # Get all tables in the database
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        all_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📋 Total tables in database: {len(all_tables)}")
        print(f"📋 Expected tables with tenant_id: {len(expected_tables_with_tenant_id)}\n")
        
        tables_with_tenant_id = []
        tables_without_tenant_id = []
        
        for table_name in expected_tables_with_tenant_id:
            if table_name not in all_tables:
                print(f"  ⚠️  Table '{table_name}' does not exist in database")
                continue
                
            # Check if tenant_id column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = 'tenant_id'
            """, (table_name,))
            
            if cursor.fetchone():
                tables_with_tenant_id.append(table_name)
                print(f"  ✅ {table_name} - HAS tenant_id")
            else:
                tables_without_tenant_id.append(table_name)
                print(f"  ❌ {table_name} - MISSING tenant_id")
        
        print("\n" + "=" * 70)
        print("📊 SUMMARY:")
        print("=" * 70)
        print(f"✅ Tables WITH tenant_id: {len(tables_with_tenant_id)}")
        if tables_with_tenant_id:
            print(f"   {', '.join(tables_with_tenant_id)}")
        
        print(f"\n❌ Tables WITHOUT tenant_id: {len(tables_without_tenant_id)}")
        if tables_without_tenant_id:
            print(f"   {', '.join(tables_without_tenant_id)}")
        
        print("\n" + "=" * 70)
        if tables_without_tenant_id:
            print("⚠️  WARNING: Code expects tenant_id on these tables but database is missing it!")
            print("⚠️  This will cause 'column tenant_id does not exist' errors!")
            print("\n💡 SOLUTION: Run migrate_add_tenant_id.py to add missing columns")
        else:
            print("✅ All expected tables have tenant_id column")
        print("=" * 70)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
