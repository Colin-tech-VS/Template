#!/usr/bin/env python3
"""
Script simple pour inspecter l'état actuel des tenants et des données.
"""

import os
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Mock DATABASE_URL if not set (for inspection only)
if not os.environ.get('SUPABASE_DB_URL') and not os.environ.get('DATABASE_URL'):
    print("⚠️  Aucune base de données configurée")
    print("Ce script nécessite SUPABASE_DB_URL ou DATABASE_URL")
    print("\nPour les tests, vous pouvez utiliser:")
    print("  export DATABASE_URL='postgresql://user:pass@host:5432/db'")
    sys.exit(1)

from database import get_db_connection

def inspect_database():
    """Inspecte l'état actuel de la base de données"""
    
    print("="*80)
    print("INSPECTION DE LA BASE DE DONNÉES")
    print("="*80)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Inspecter la table tenants
            print("\n📋 TABLE TENANTS")
            print("-"*80)
            try:
                cursor.execute("SELECT * FROM tenants ORDER BY id")
                tenants = cursor.fetchall()
                
                if not tenants:
                    print("⚠️  Aucun tenant trouvé dans la table 'tenants'")
                else:
                    print(f"Nombre de tenants: {len(tenants)}\n")
                    for tenant in tenants:
                        if isinstance(tenant, dict):
                            print(f"  ID: {tenant['id']}")
                            print(f"  Host: {tenant['host']}")
                            print(f"  Name: {tenant.get('name', 'N/A')}")
                            print(f"  Created: {tenant.get('created_at', 'N/A')}")
                        else:
                            print(f"  ID: {tenant[0]}")
                            print(f"  Host: {tenant[1]}")
                            print(f"  Name: {tenant[2] if len(tenant) > 2 else 'N/A'}")
                            print(f"  Created: {tenant[3] if len(tenant) > 3 else 'N/A'}")
                        print()
            except Exception as e:
                print(f"❌ Erreur lors de la lecture de la table tenants: {e}")
            
            # 2. Inspecter saas_sites
            print("\n📋 TABLE SAAS_SITES")
            print("-"*80)
            try:
                cursor.execute("""
                    SELECT id, user_id, status, sandbox_url, final_domain, tenant_id, created_at
                    FROM saas_sites 
                    ORDER BY id
                """)
                sites = cursor.fetchall()
                
                if not sites:
                    print("⚠️  Aucun site trouvé dans la table 'saas_sites'")
                else:
                    print(f"Nombre de sites: {len(sites)}\n")
                    for site in sites:
                        if isinstance(site, dict):
                            print(f"  Site ID: {site['id']}")
                            print(f"  User ID: {site.get('user_id', 'N/A')}")
                            print(f"  Status: {site.get('status', 'N/A')}")
                            print(f"  Sandbox URL: {site.get('sandbox_url', 'N/A')}")
                            print(f"  Final Domain: {site.get('final_domain', 'N/A')}")
                            print(f"  Tenant ID: {site.get('tenant_id', 'N/A')}")
                            print(f"  Created: {site.get('created_at', 'N/A')}")
                        else:
                            print(f"  Site ID: {site[0]}")
                            print(f"  User ID: {site[1]}")
                            print(f"  Status: {site[2]}")
                            print(f"  Sandbox URL: {site[3]}")
                            print(f"  Final Domain: {site[4]}")
                            print(f"  Tenant ID: {site[5]}")
                            print(f"  Created: {site[6]}")
                        print()
            except Exception as e:
                print(f"❌ Erreur lors de la lecture de saas_sites: {e}")
            
            # 3. Statistiques par table
            print("\n📊 STATISTIQUES PAR TABLE")
            print("-"*80)
            
            tables_with_tenant = [
                'users', 'paintings', 'carts', 'cart_items', 'orders', 'order_items',
                'exhibitions', 'custom_requests', 'notifications', 'favorites',
                'settings', 'saas_sites', 'stripe_events'
            ]
            
            for table in tables_with_tenant:
                try:
                    # Vérifier si la table existe
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_name = %s
                    """, (table,))
                    
                    if not cursor.fetchone():
                        print(f"  {table}: Table n'existe pas")
                        continue
                    
                    # Compter les lignes par tenant_id
                    cursor.execute(f"""
                        SELECT tenant_id, COUNT(*) as count 
                        FROM {table} 
                        GROUP BY tenant_id 
                        ORDER BY tenant_id
                    """)
                    results = cursor.fetchall()
                    
                    if not results:
                        print(f"  {table}: Aucune donnée")
                    else:
                        counts = []
                        for row in results:
                            if isinstance(row, dict):
                                tenant_id = row.get('tenant_id', 'NULL')
                                count = row.get('count', 0)
                            else:
                                tenant_id = row[0] if row[0] is not None else 'NULL'
                                count = row[1]
                            counts.append(f"tenant_id={tenant_id}: {count} ligne(s)")
                        
                        print(f"  {table}: {', '.join(counts)}")
                        
                except Exception as e:
                    print(f"  {table}: Erreur - {e}")
            
            print("\n" + "="*80)
            print("✅ Inspection terminée")
            print("="*80)
            
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    inspect_database()
