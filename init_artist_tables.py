"""
Script d'initialisation des tables artistes dans Supabase
À exécuter une seule fois pour créer les tables template_artists et artworks_artist_actions
"""

import os
import psycopg2
from urllib.parse import urlparse
import sys

# Configuration base de données
DATABASE_URL = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ Erreur: SUPABASE_DB_URL ou DATABASE_URL non définie")
    print("💡 Définissez-la avec: export SUPABASE_DB_URL='postgresql://...'")
    sys.exit(1)

# Parser l'URL
result = urlparse(DATABASE_URL)
DB_CONFIG = {
    'host': result.hostname,
    'port': result.port or 5432,
    'database': result.path[1:] if result.path else '',
    'user': result.username,
    'password': result.password,
    'sslmode': 'require'
}

print(f"🔧 Connexion à Supabase: {DB_CONFIG['host']}/{DB_CONFIG['database']}")

# SQL pour créer les tables
SQL_CREATE_TABLES = """
-- Table template_artists: Stocke les informations des artistes
CREATE TABLE IF NOT EXISTS template_artists (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    bio TEXT,
    website TEXT,
    price DECIMAL(10, 2) DEFAULT 500.00,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table artworks_artist_actions: Historique des actions sur les artistes
CREATE TABLE IF NOT EXISTS artworks_artist_actions (
    id SERIAL PRIMARY KEY,
    artist_id INTEGER NOT NULL REFERENCES template_artists(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('created', 'updated', 'approved', 'rejected', 'deleted')),
    action_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    performed_by TEXT,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_template_artists_email ON template_artists(email);
CREATE INDEX IF NOT EXISTS idx_template_artists_status ON template_artists(status);
CREATE INDEX IF NOT EXISTS idx_template_artists_created_at ON template_artists(created_at);
CREATE INDEX IF NOT EXISTS idx_artworks_artist_actions_artist_id ON artworks_artist_actions(artist_id);
CREATE INDEX IF NOT EXISTS idx_artworks_artist_actions_action_date ON artworks_artist_actions(action_date);

-- Fonction pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger pour auto-update de updated_at
DROP TRIGGER IF EXISTS update_template_artists_updated_at ON template_artists;
CREATE TRIGGER update_template_artists_updated_at
    BEFORE UPDATE ON template_artists
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Commentaires pour documentation
COMMENT ON TABLE template_artists IS 'Artistes du site vitrine Artworksdigital';
COMMENT ON TABLE artworks_artist_actions IS 'Historique des actions effectuées sur les artistes';
COMMENT ON COLUMN template_artists.status IS 'Statut de l artiste: pending, approved, rejected';
COMMENT ON COLUMN artworks_artist_actions.action IS 'Type d action: created, updated, approved, rejected, deleted';
COMMENT ON COLUMN artworks_artist_actions.action_date IS 'Date de l action (différent de created_at)';
"""

def create_artist_tables():
    """
    Crée les tables template_artists et artworks_artist_actions dans Supabase
    """
    try:
        # Connexion à la base de données
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("📊 Création des tables artistes...")
        
        # Exécuter le script SQL
        cursor.execute(SQL_CREATE_TABLES)
        conn.commit()
        
        print("✅ Tables créées avec succès:")
        print("   - template_artists")
        print("   - artworks_artist_actions")
        print("   - Indexes de performance")
        print("   - Trigger auto-update updated_at")
        
        # Vérifier que les tables existent
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('template_artists', 'artworks_artist_actions')
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print(f"\n📋 Tables vérifiées: {len(tables)} trouvées")
        for table in tables:
            print(f"   ✓ {table[0]}")
        
        # Afficher la structure de template_artists
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'template_artists'
            ORDER BY ordinal_position
        """)
        
        print(f"\n📐 Structure template_artists:")
        columns = cursor.fetchall()
        for col in columns:
            nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col[3]}" if col[3] else ""
            print(f"   • {col[0]}: {col[1]} {nullable}{default}")
        
        # Afficher la structure de artworks_artist_actions
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'artworks_artist_actions'
            ORDER BY ordinal_position
        """)
        
        print(f"\n📐 Structure artworks_artist_actions:")
        columns = cursor.fetchall()
        for col in columns:
            nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
            default = f" DEFAULT {col[3]}" if col[3] else ""
            print(f"   • {col[0]}: {col[1]} {nullable}{default}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Initialisation terminée avec succès!")
        print("\n📚 Prochaines étapes:")
        print("   1. Définir SUPABASE_URL et SUPABASE_ANON_KEY dans .env")
        print("   2. Définir SUPABASE_SERVICE_KEY pour les opérations admin")
        print("   3. Tester les endpoints avec: python test_artists_api.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la création des tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("="*60)
    print("🚀 INITIALISATION DES TABLES ARTISTES - SUPABASE")
    print("="*60)
    print()
    
    success = create_artist_tables()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
