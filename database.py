"""
Module de gestion de base de données avec support SQLite (local) et PostgreSQL (production)
Détection automatique via la variable d'environnement DATABASE_URL (Render)
"""

import os
import sqlite3
from contextlib import contextmanager

# Détecter l'environnement
DATABASE_URL = os.environ.get('DATABASE_URL')
IS_POSTGRES = DATABASE_URL is not None

if IS_POSTGRES:
    import psycopg2
    import psycopg2.extras
    from urllib.parse import urlparse
    
    # Parser l'URL PostgreSQL
    result = urlparse(DATABASE_URL)
    DB_CONFIG = {
        'host': result.hostname,
        'port': result.port,
        'database': result.path[1:],
        'user': result.username,
        'password': result.password
    }
else:
    DB_PATH = 'paintings.db'


def _get_site_db_path(user_id=None):
    """Retourne le chemin de la DB pour un site spécifique"""
    if user_id:
        return f'site_{user_id}.db'
    return DB_PATH


@contextmanager
def get_db_connection(user_id=None):
    """
    Context manager pour obtenir une connexion à la base de données
    Args:
        user_id: ID de l'utilisateur/site. Si None, utilise la DB centrale
    Usage: 
        with get_db_connection(user_id) as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    if IS_POSTGRES:
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            yield conn
        finally:
            conn.close()
    else:
        db_path = _get_site_db_path(user_id)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def get_db(user_id=None):
    """
    Retourne une connexion simple
    Args:
        user_id: ID de l'utilisateur/site. Si None, utilise la DB centrale
    """
    if IS_POSTGRES:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    else:
        db_path = _get_site_db_path(user_id)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn


def adapt_query(query):
    """
    Adapte une requête SQLite pour PostgreSQL
    - AUTOINCREMENT -> SERIAL
    - ? -> %s (paramètres)
    - RANDOM() -> RANDOM() (compatible)
    - CURRENT_TIMESTAMP reste identique
    """
    if not IS_POSTGRES:
        return query
    
    # Remplacer INTEGER PRIMARY KEY AUTOINCREMENT par SERIAL PRIMARY KEY
    query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    query = query.replace('AUTOINCREMENT', '')
    
    # Remplacer les ? par %s pour les paramètres PostgreSQL
    # ATTENTION: Ne pas remplacer dans les chaînes de texte
    query = query.replace('?', '%s')
    
    return query


def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=True, user_id=None):
    """
    Exécute une requête avec gestion automatique de la connexion
    
    Args:
        query: La requête SQL
        params: Tuple ou liste des paramètres
        fetch_one: Si True, retourne un seul résultat
        fetch_all: Si True, retourne tous les résultats
        commit: Si True, commit les changements
        user_id: ID de l'utilisateur/site. Si None, utilise la DB centrale
        
    Returns:
        Le résultat de la requête selon fetch_one/fetch_all
    """
    with get_db_connection(user_id=user_id) as conn:
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


def create_table_if_not_exists(table_name, columns, user_id=None):
    """
    Crée une table si elle n'existe pas
    Args:
        table_name: Nom de la table
        columns: dict {"column_name": "TYPE CONSTRAINTS"}
        user_id: ID de l'utilisateur/site pour la DB spécifique
    """
    col_defs = ", ".join([f"{name} {ctype}" for name, ctype in columns.items()])
    query = f"CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})"
    try:
        execute_query(query, user_id=user_id)
    except Exception as e:
        # Ignore DuplicateTable error for PostgreSQL
        if hasattr(e, 'pgcode') and e.pgcode == '42P07':
            print(f"Table '{table_name}' existe déjà, on continue.")
        elif 'already exists' in str(e):
            print(f"Table '{table_name}' existe déjà, on continue.")
        else:
            raise


def add_column_if_not_exists(table_name, column_name, column_type, user_id=None):
    """
    Ajoute une colonne si elle n'existe pas
    Args:
        table_name: Nom de la table
        column_name: Nom de la colonne
        column_type: Type de la colonne
        user_id: ID de l'utilisateur/site pour la DB spécifique
    Attention: syntaxe différente entre SQLite et PostgreSQL
    """
    with get_db_connection(user_id=user_id) as conn:
        cursor = conn.cursor()
        
        if IS_POSTGRES:
            # PostgreSQL: vérifier dans information_schema
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name=%s AND column_name=%s
            """, (table_name, column_name))
            if not cursor.fetchone():
                # Adapter le type pour PostgreSQL
                col_type_pg = column_type.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY').replace('AUTOINCREMENT', '')
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {col_type_pg}"
                try:
                    cursor.execute(sql)
                    conn.commit()
                    print(f"Colonne '{column_name}' ajoutée à '{table_name}'")
                except Exception as e:
                    print(f"Erreur ajout colonne '{column_name}' à '{table_name}': {e}")
        else:
            # SQLite: PRAGMA table_info
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_cols = [col[1] for col in cursor.fetchall()]
            if column_name not in existing_cols:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                cursor.execute(sql)
                conn.commit()
                print(f"Colonne '{column_name}' ajoutée à '{table_name}'")


def get_last_insert_id(cursor):
    """
    Récupère le dernier ID inséré
    SQLite: lastrowid
    PostgreSQL: RETURNING id ou currval
    """
    if IS_POSTGRES:
        # PostgreSQL utilise RETURNING id dans l'INSERT
        # Ou on peut utiliser currval si on connaît la séquence
        return cursor.fetchone()[0] if cursor.description else None
    else:
        return cursor.lastrowid


# Constantes pour compatibilité
PARAM_PLACEHOLDER = '%s' if IS_POSTGRES else '?'
AUTOINCREMENT = 'SERIAL' if IS_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'


def create_indexes_if_not_exists(user_id=None):
    """
    Crée des index sur les colonnes fréquemment requêtées pour améliorer les performances
    Args:
        user_id: Si fourni, crée les index pour la DB d'un site spécifique
    """
    indexes = [
        # Index sur les colonnes fréquemment utilisées dans les requêtes
        ("idx_paintings_category", "paintings", "category"),
        ("idx_paintings_status", "paintings", "status"),
        ("idx_paintings_display_order", "paintings", "display_order"),
        ("idx_paintings_quantity", "paintings", "quantity"),
        ("idx_orders_user_id", "orders", "user_id"),
        ("idx_orders_status", "orders", "status"),
        ("idx_order_items_order_id", "order_items", "order_id"),
        ("idx_order_items_painting_id", "order_items", "painting_id"),
        ("idx_cart_items_cart_id", "cart_items", "cart_id"),
        ("idx_cart_items_painting_id", "cart_items", "painting_id"),
        ("idx_carts_user_id", "carts", "user_id"),
        ("idx_carts_session_id", "carts", "session_id"),
        ("idx_favorites_user_id", "favorites", "user_id"),
        ("idx_favorites_painting_id", "favorites", "painting_id"),
    ]
    
    with get_db_connection(user_id=user_id) as conn:
        cursor = conn.cursor()
        
        for index_name, table_name, column_name in indexes:
            try:
                # CREATE INDEX IF NOT EXISTS est compatible SQLite et PostgreSQL
                sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
                cursor.execute(sql)
            except Exception as e:
                # L'index peut déjà exister ou la table peut ne pas exister
                print(f"Info: Index {index_name} non créé - {e}")
        
        # Un seul commit pour toutes les créations d'index
        conn.commit()
    
    print(f"Index de performance créés/vérifiés")


def init_database(user_id=None):
    """
    Initialise les tables de la base de données
    Args:
        user_id: Si fourni, initialise la DB d'un site spécifique
    """
    from app import TABLES
    
    for table_name, columns in TABLES.items():
        create_table_if_not_exists(table_name, columns, user_id=user_id)
    
    # Créer les index de performance
    create_indexes_if_not_exists(user_id=user_id)
    
    db_type = 'PostgreSQL' if IS_POSTGRES else 'SQLite'
    if user_id:
        print(f"Base de données site_{user_id} initialisée ({db_type})")
    else:
        print(f"Base de données centrale initialisée ({db_type})")
