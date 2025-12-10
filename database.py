"""
Module de gestion de base de données Supabase/PostgreSQL
Migration complète depuis SQLite vers Supabase/Postgres
"""

import os
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse
from contextlib import contextmanager

# Configuration Supabase/PostgreSQL
# Priorité 1: SUPABASE_DB_URL (nouvelle variable)
# Priorité 2: DATABASE_URL (compatibilité)
DATABASE_URL = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("⚠️  ATTENTION: Aucune connexion PostgreSQL/Supabase configurée!")
    print("⚠️  Définissez SUPABASE_DB_URL ou DATABASE_URL dans les variables d'environnement")
    print("⚠️  Format: postgresql://user:password@host:port/database")
    # En production, on doit avoir une DB URL
    # En développement local, utiliser une DB Supabase de test
    raise ValueError("DATABASE_URL non définie - impossible de démarrer sans base de données")

# Parser l'URL PostgreSQL/Supabase
try:
    result = urlparse(DATABASE_URL)
    DB_CONFIG = {
        'host': result.hostname,
        'port': result.port or 5432,
        'database': result.path[1:] if result.path else '',
        'user': result.username,
        'password': result.password,
        'sslmode': 'require'  # Supabase nécessite SSL
    }
    print(f"✅ Configuration Supabase/Postgres: {DB_CONFIG['host']}/{DB_CONFIG['database']}")
except Exception as e:
    print(f"❌ Erreur parsing DATABASE_URL: {e}")
    raise

# Constantes
IS_POSTGRES = True  # Toujours PostgreSQL maintenant


@contextmanager
def get_db_connection():
    """
    Context manager pour obtenir une connexion Supabase/PostgreSQL
    Usage: 
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


def get_db(user_id=None):
    """
    Retourne une connexion Supabase/PostgreSQL.
    
    Args:
        user_id: ID de l'utilisateur/site (pour compatibilité multi-tenant future)
                 Actuellement ignoré car on utilise une seule base Supabase
    
    Returns:
        psycopg2.connection: Connexion PostgreSQL avec RealDictCursor
    """
    conn = psycopg2.connect(**DB_CONFIG)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn


def adapt_query(query):
    """
    Adapte une requête pour PostgreSQL/Supabase
    - Remplace les placeholders SQLite (?) par PostgreSQL (%s)
    - Gère les types de données spécifiques
    """
    # Remplacer les ? par %s pour les paramètres PostgreSQL
    query = query.replace('?', '%s')
    
    # Remplacer INTEGER PRIMARY KEY AUTOINCREMENT par SERIAL PRIMARY KEY
    query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    query = query.replace('AUTOINCREMENT', '')
    
    return query


def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=True):
    """
    Exécute une requête PostgreSQL/Supabase avec gestion automatique de la connexion
    
    Args:
        query: La requête SQL
        params: Tuple ou liste des paramètres
        fetch_one: Si True, retourne un seul résultat
        fetch_all: Si True, retourne tous les résultats
        commit: Si True, commit les changements
        
    Returns:
        Le résultat de la requête selon fetch_one/fetch_all
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        adapted_query = adapt_query(query)
        
        if params:
            cursor.execute(adapted_query, params)
        else:
            cursor.execute(adapted_query)
        
        result = None
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        
        if commit:
            conn.commit()
        
        return result


def create_table_if_not_exists(table_name, columns):
    """
    Crée une table Supabase/PostgreSQL si elle n'existe pas
    Args:
        table_name: Nom de la table
        columns: dict {"column_name": "TYPE CONSTRAINTS"}
    """
    col_defs = ", ".join([f"{name} {ctype}" for name, ctype in columns.items()])
    query = f"CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})"
    execute_query(query)
    print(f"✅ Table '{table_name}' créée ou vérifiée dans Supabase")


def add_column_if_not_exists(table_name, column_name, column_type):
    """
    Ajoute une colonne PostgreSQL/Supabase si elle n'existe pas
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # PostgreSQL: vérifier dans information_schema
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name=%s AND column_name=%s
        """, (table_name, column_name))
        
        if not cursor.fetchone():
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            cursor.execute(sql)
            conn.commit()
            print(f"✅ Colonne '{column_name}' ajoutée à '{table_name}' dans Supabase")


def get_last_insert_id(cursor):
    """
    Récupère le dernier ID inséré (PostgreSQL/Supabase)
    PostgreSQL utilise RETURNING id dans l'INSERT ou currval
    """
    return cursor.fetchone()[0] if cursor.description else None


# Constantes pour compatibilité
PARAM_PLACEHOLDER = '%s'  # PostgreSQL/Supabase uniquement
AUTOINCREMENT = 'SERIAL'  # PostgreSQL/Supabase uniquement


def init_database(user_id=None):
    """
    Initialise les tables de la base de données Supabase/PostgreSQL
    
    Args:
        user_id: ID utilisateur pour compatibilité multi-tenant (non utilisé actuellement)
    """
    # Import circulaire évité en important ici
    from app import TABLES
    
    print(f"🔧 Initialisation de la base de données Supabase/Postgres...")
    
    for table_name, columns in TABLES.items():
        try:
            create_table_if_not_exists(table_name, columns)
        except Exception as e:
            print(f"⚠️  Erreur création table '{table_name}': {e}")
    
    print(f"✅ Base de données Supabase/Postgres initialisée avec succès")

