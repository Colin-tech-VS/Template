"""
Script de vérification du schéma de la base de données Supabase/PostgreSQL
Affiche le schéma de la table settings et les paramètres Stripe
"""

import os
import sys

# Vérifier que SUPABASE_DB_URL est définie
SUPABASE_URL = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')
if not SUPABASE_URL:
    print("❌ Erreur: SUPABASE_DB_URL ou DATABASE_URL non définie")
    print("💡 Définissez-la avec: export SUPABASE_DB_URL='postgresql://...'")
    sys.exit(1)

try:
    from database import get_db  # Returns connection with RealDictCursor configured
    
    print("🔍 Vérification du schéma de la base de données Supabase")
    print("=" * 70)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Afficher le schéma de la table settings
    print("\n📊 Schéma de la table 'settings':")
    print("-" * 70)
    cursor.execute("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'settings'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    if columns:
        for col in columns:
            # RealDictCursor allows dict-style access
            col_name = col['column_name']
            col_type = col['data_type']
            col_length = col['character_maximum_length'] or ''
            col_null = col['is_nullable']
            print(f"  • {col_name}: {col_type}{f'({col_length})' if col_length else ''} - Nullable: {col_null}")
    else:
        print("  ⚠️  Table 'settings' introuvable")
    
    # Afficher les paramètres Stripe
    print("\n🔐 Paramètres Stripe stockés:")
    print("-" * 70)
    cursor.execute("""
        SELECT * FROM settings 
        WHERE key LIKE %s OR key = %s
        ORDER BY key
    """, ('stripe%', 'export_api_key'))
    
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            key = row['key']
            value = row['value']
            
            # Masquer les valeurs sensibles
            if 'sk_' in str(value) or 'secret' in key.lower():
                masked_value = value[:6] + '...' + value[-4:] if len(value) > 10 else '***'
            else:
                masked_value = value
            
            print(f"  • Key: {key}")
            print(f"    Value: {masked_value}")
    else:
        print("  ℹ️  Aucun paramètre Stripe trouvé dans la base")
    
    print()
    conn.close()
    print("✅ Vérification terminée")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
