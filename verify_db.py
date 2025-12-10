#!/usr/bin/env python
"""
Script de vérification de la base de données Supabase/PostgreSQL
Affiche les clés Stripe et autres paramètres importants
"""

import os
import sys

SUPABASE_URL = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')
if not SUPABASE_URL:
    print("❌ Erreur: SUPABASE_DB_URL ou DATABASE_URL non définie")
    print("💡 Définissez-la avec: export SUPABASE_DB_URL='postgresql://...'")
    sys.exit(1)

try:
    from database import get_db
    
    conn = get_db()
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("🔍 VÉRIFICATION DE LA BASE DE DONNÉES SUPABASE - Clés Stripe")
    print("="*80)
    
    cursor.execute("SELECT key, value FROM settings WHERE key LIKE %s", ('stripe%',))
    rows = cursor.fetchall()
    
    if not rows:
        print("\n⚠️  Aucune clé Stripe trouvée dans la base de données")
    else:
        for row in rows:
            key = row['key']
            value = row['value']
            
            # Masquer les valeurs sensibles
            if len(value) > 30:
                display_value = value[:20] + "..." + value[-10:]
            else:
                display_value = value
            
            print(f"\n✅ [KEY] {key}")
            print(f"   [VALUE] {display_value}")
            print(f"   [LENGTH] {len(value)} caractères")
    
    # Vérifier d'autres paramètres importants
    print("\n" + "-"*80)
    print("📊 Autres paramètres importants:")
    print("-"*80)
    
    cursor.execute("""
        SELECT key, value FROM settings 
        WHERE key IN ('site_name', 'dashboard_api_base', 'dashboard_id', 'export_api_key')
        ORDER BY key
    """)
    
    other_settings = cursor.fetchall()
    if other_settings:
        for row in other_settings:
            key = row['key']
            value = row['value']
            
            # Masquer export_api_key
            if key == 'export_api_key' and len(value) > 20:
                display_value = value[:10] + "..." + value[-6:]
            else:
                display_value = value[:50] + "..." if len(value) > 50 else value
            
            print(f"   • {key}: {display_value}")
    else:
        print("   ℹ️  Aucun paramètre trouvé")
    
    conn.close()
    
    print("\n" + "="*80)
    print("✅ Vérification complète")
    print("="*80 + "\n")

except Exception as e:
    print(f"\n❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
