"""
Module de gestion de base de données Supabase/PostgreSQL
Migration complète depuis SQLite vers Supabase/Postgres
OPTIMISÉ: Connection pooling, logging de performance
"""

import os
from urllib.parse import urlparse
from contextlib import contextmanager
import time
import atexit
import logging

# Prefer psycopg (psycopg3) when available (provides psycopg_pool and wheels
# compatible with newer Python versions). Fall back to psycopg2 if needed.
USING_PSYCOPG3 = False
try:
    import psycopg as psycopg3  # type: ignore
    from psycopg_pool import ConnectionPool as PsycopgPool  # type: ignore
    from psycopg.rows import dict_row  # type: ignore
    USING_PSYCOPG3 = True
except Exception:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool

# Configuration du logging pour la performance
logging.basicConfig(level=logging.INFO)
perf_logger = logging.getLogger('db.performance')

# Configuration Supabase/PostgreSQL
# Priorité 1: SUPABASE_DB_URL (nouvelle variable)
# Priorité 2: DATABASE_URL (compatibilité)
DATABASE_URL = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("[WARNING] Aucune connexion PostgreSQL/Supabase configurée!")
    print("[WARNING] Définissez SUPABASE_DB_URL ou DATABASE_URL dans les variables d'environnement")
    print("[WARNING] Format: postgresql://user:password@host:port/database")
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

# =========================================
# CONNECTION POOL GLOBAL (OPTIMISATION)
# =========================================
# Pool de connexions thread-safe pour réutiliser les connexions
# Réduit drastiquement le temps de connexion (de ~100ms à <1ms)
CONNECTION_POOL = None

def init_connection_pool(minconn=1, maxconn=5):
    """
    Initialise le pool de connexions PostgreSQL/Supabase
    
    Args:
        minconn: Nombre minimum de connexions maintenues (réduit pour Supabase)
        maxconn: Nombre maximum de connexions autorisées (limité par Supabase)
    
    IMPORTANT: Supabase en mode Session pooling limite à 10-15 connexions par projet
    minconn=1, maxconn=5 est optimal pour éviter "MaxClientsInSessionMode" errors
    
    Returns:
        psycopg2.pool.ThreadedConnectionPool
    """
    global CONNECTION_POOL
    
    if CONNECTION_POOL is not None:
        return CONNECTION_POOL
    
    try:
        if USING_PSYCOPG3:
            # psycopg_pool expects a connection string (DATABASE_URL)
            CONNECTION_POOL = PsycopgPool(conninfo=DATABASE_URL, min_size=minconn, max_size=maxconn)
            print(f"✅ psycopg ConnectionPool initialisé: {minconn}-{maxconn} connexions")
        else:
            CONNECTION_POOL = psycopg2.pool.ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                **DB_CONFIG
            )
            print(f"✅ psycopg2 ThreadedConnectionPool initialisé: {minconn}-{maxconn} connexions (Supabase Session mode)")
        return CONNECTION_POOL
    except Exception as e:
        print(f"❌ Erreur initialisation connection pool: {e}")
        raise

def get_pool_connection():
    """
    Obtient une connexion depuis le pool
    
    Returns:
        psycopg2.connection
    """
    global CONNECTION_POOL
    
    if CONNECTION_POOL is None:
        init_connection_pool()

    if USING_PSYCOPG3:
        # For psycopg3 we prefer using the context-manager API via get_db_connection();
        # this function is kept for compatibility but shouldn't be used for psycopg3.
        raise RuntimeError("get_pool_connection() is not supported when using psycopg (psycopg3); use get_db_connection() or get_db() instead")

    try:
        return CONNECTION_POOL.getconn()
    except Exception as e:
        perf_logger.error(f"Erreur obtention connexion du pool: {e}")
        raise

def return_pool_connection(conn):
    """
    Retourne une connexion au pool
    
    Args:
        conn: Connexion à retourner
    """
    global CONNECTION_POOL
    
    if CONNECTION_POOL is None or conn is None:
        return

    if USING_PSYCOPG3:
        # psycopg3 pool connections are returned by exiting the context manager.
        # If someone obtained a raw connection, close it normally.
        try:
            conn.close()
        except Exception:
            pass
        return

    CONNECTION_POOL.putconn(conn)

def close_connection_pool():
    """Ferme toutes les connexions du pool"""
    global CONNECTION_POOL
    
    if CONNECTION_POOL is not None:
        try:
            if USING_PSYCOPG3:
                # psycopg3 ConnectionPool: close background workers cleanly
                try:
                    CONNECTION_POOL.close()
                except Exception:
                    pass
                # wait_closed exists on newer psycopg_pool implementations
                try:
                    wait = getattr(CONNECTION_POOL, 'wait_closed', None)
                    if callable(wait):
                        wait(5.0)
                except Exception:
                    pass
            else:
                # psycopg2 ThreadedConnectionPool
                try:
                    CONNECTION_POOL.closeall()
                except Exception:
                    pass
        finally:
            CONNECTION_POOL = None
            print("✅ Connection pool fermé")


# Register atexit handler to ensure the pool is closed on process exit.
# This avoids psycopg.pool warnings about background threads not stopping.
try:
    atexit.register(close_connection_pool)
except Exception:
    pass


class ConnectionWrapper:
    """
    Wrapper pour une connexion PostgreSQL/Supabase qui retourne automatiquement
    la connexion au pool lors du close() au lieu de la fermer réellement.
    
    Cette classe résout le problème d'AttributeError lorsqu'on tente de réassigner
    conn.close qui est read-only dans psycopg2.
    """
    
    def __init__(self, connection):
        # connection: actual DB connection object
        # release_func: optional callable to release the connection back to pool
        connection_obj = connection
        release_func = None
        if isinstance(connection, tuple) and len(connection) == 2:
            # (conn, release_func) tuple provided
            connection_obj, release_func = connection

        object.__setattr__(self, '_connection', connection_obj)
        object.__setattr__(self, '_release_func', release_func)
        object.__setattr__(self, '_closed', False)
    
    def __getattr__(self, name):
        """Délègue tous les attributs non définis à la connexion sous-jacente"""
        return getattr(self._connection, name)
    
    def __setattr__(self, name, value):
        """Délègue l'assignation des attributs à la connexion sous-jacente"""
        if name in ('_connection', '_closed'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._connection, name, value)
    
    def __enter__(self):
        """Support pour le context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Retourne la connexion au pool lors de la sortie du context manager"""
        self.close()
        return False
    
    def close(self):
        """
        Retourne la connexion au pool au lieu de la fermer réellement.
        Peut être appelé plusieurs fois sans problème.
        """
        if not self._closed:
            # If a release function (from psycopg3 pool) is provided, call it; else use putconn
            if getattr(self, '_release_func', None):
                try:
                    # release_func follows contextmanager __exit__(exc_type, exc, tb) signature
                    self._release_func(None, None, None)
                except Exception:
                    try:
                        return_pool_connection(self._connection)
                    except Exception:
                        pass
            else:
                return_pool_connection(self._connection)
            object.__setattr__(self, '_closed', True)
    
    @property
    def closed(self):
        """Indique si la connexion est fermée (retournée au pool)"""
        return self._closed


@contextmanager
def get_db_connection():
    """
    Context manager pour obtenir une connexion Supabase/PostgreSQL
    OPTIMISÉ: Utilise le connection pool au lieu de créer une nouvelle connexion
    
    Usage: 
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    start_time = time.time()
    # Branch behavior depending on driver
    if USING_PSYCOPG3:
        if CONNECTION_POOL is None:
            init_connection_pool()
        ctx = CONNECTION_POOL.connection()
        conn = ctx.__enter__()
        conn_time = (time.time() - start_time) * 1000
        if conn_time > 10:
            perf_logger.warning(f"Connexion lente depuis le pool: {conn_time:.2f}ms")
        try:
            yield conn
        finally:
            # release connection back to pool
            try:
                ctx.__exit__(None, None, None)
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
    else:
        conn = get_pool_connection()
        conn_time = (time.time() - start_time) * 1000
        # Logger si la connexion prend trop de temps
        if conn_time > 10:
            perf_logger.warning(f"Connexion lente depuis le pool: {conn_time:.2f}ms")
        try:
            yield conn
        finally:
            return_pool_connection(conn)


def get_db(user_id=None):
    """
    Retourne une connexion Supabase/PostgreSQL depuis le pool.
    OPTIMISÉ: Réutilise les connexions au lieu d'en créer de nouvelles
    
    Args:
        user_id: ID de l'utilisateur/site (pour compatibilité multi-tenant future)
                 Actuellement ignoré car on utilise une seule base Supabase
    
    Returns:
        ConnectionWrapper: Wrapper de connexion PostgreSQL avec RealDictCursor
        
    IMPORTANT: L'appelant doit fermer la connexion avec conn.close()
               qui la retournera au pool
    
    Note: Utilise maintenant ConnectionWrapper pour éviter l'erreur AttributeError
          lors de la réassignation de conn.close qui est read-only dans psycopg2.
    """
    start_time = time.time()
    if USING_PSYCOPG3:
        if CONNECTION_POOL is None:
            init_connection_pool()
        ctx = CONNECTION_POOL.connection()
        conn = ctx.__enter__()
        # use dict_row as row factory to emulate RealDictCursor
        try:
            conn.row_factory = dict_row
        except Exception:
            pass

        conn_time = (time.time() - start_time) * 1000
        if conn_time > 10:
            perf_logger.warning(f"get_db() lent: {conn_time:.2f}ms")

        # Return a wrapper that knows how to release the pooled connection
        return ConnectionWrapper((conn, ctx.__exit__))

    # psycopg2 path
    conn = get_pool_connection()
    conn.cursor_factory = psycopg2.extras.RealDictCursor

    conn_time = (time.time() - start_time) * 1000
    if conn_time > 10:
        perf_logger.warning(f"get_db() lent: {conn_time:.2f}ms")

    # Utiliser le wrapper pour gérer le close() proprement
    return ConnectionWrapper(conn)


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
    OPTIMISÉ: Utilise le connection pool et log les requêtes lentes
    
    Args:
        query: La requête SQL
        params: Tuple ou liste des paramètres
        fetch_one: Si True, retourne un seul résultat
        fetch_all: Si True, retourne tous les résultats
        commit: Si True, commit les changements
        
    Returns:
        Le résultat de la requête selon fetch_one/fetch_all
    """
    start_time = time.time()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        adapted_query = adapt_query(query)
        
        query_start = time.time()
        if params:
            cursor.execute(adapted_query, params)
        else:
            cursor.execute(adapted_query)
        query_time = (time.time() - query_start) * 1000
        
        result = None
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        
        if commit:
            conn.commit()
        
        total_time = (time.time() - start_time) * 1000
        
        # Logger les requêtes lentes (>100ms)
        if total_time > 100:
            # Tronquer la requête pour le log
            query_preview = adapted_query[:100].replace('\n', ' ')
            perf_logger.warning(
                f"Requête lente: {total_time:.2f}ms (query: {query_time:.2f}ms) - {query_preview}..."
            )
        
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
    OPTIMISÉ: Crée aussi les indexes pour améliorer les performances
    
    Args:
        user_id: ID utilisateur pour compatibilité multi-tenant (non utilisé actuellement)
    """
    # Import circulaire évité en important ici
    from app import TABLES
    
    print(f"🔧 Initialisation de la base de données Supabase/Postgres...")
    
    # Initialiser le pool de connexions
    init_connection_pool()
    
    for table_name, columns in TABLES.items():
        try:
            create_table_if_not_exists(table_name, columns)
        except Exception as e:
            print(f"⚠️  Erreur création table '{table_name}': {e}")
    
    # Créer les indexes pour optimiser les performances
    print(f"🔧 Création des indexes de performance...")
    create_performance_indexes()
    
    print(f"✅ Base de données Supabase/Postgres initialisée avec succès")


def create_performance_indexes():
    """
    Crée les indexes de base de données pour optimiser les performances des requêtes fréquentes
    
    Indexes créés:
    - users(email): Lookups lors du login
    - paintings(status, display_order): Filtrage et tri de la galerie
    - orders(status, order_date): Filtrage des commandes admin
    - order_items(order_id): JOIN avec orders
    - order_items(painting_id): JOIN avec paintings
    - cart_items(cart_id): JOIN avec carts
    - carts(session_id): Lookup du panier par session
    - carts(user_id): Lookup du panier par utilisateur
    - notifications(user_id, is_read): Filtrage des notifications
    - exhibitions(date): Tri chronologique
    - custom_requests(status): Filtrage par statut
    - settings(key): Lookup rapide des settings
    """
    indexes = [
        # Users - login rapide
        ("idx_users_email", "users", "email"),
        
        # Paintings - galerie et filtres
        ("idx_paintings_status", "paintings", "status"),
        ("idx_paintings_display_order", "paintings", "display_order"),
        ("idx_paintings_category", "paintings", "category"),
        
        # Orders - gestion des commandes
        ("idx_orders_status", "orders", "status"),
        ("idx_orders_date", "orders", "order_date"),
        ("idx_orders_user_id", "orders", "user_id"),
        
        # Order items - JOINs
        ("idx_order_items_order_id", "order_items", "order_id"),
        ("idx_order_items_painting_id", "order_items", "painting_id"),
        
        # Carts - panier utilisateur
        ("idx_carts_session_id", "carts", "session_id"),
        ("idx_carts_user_id", "carts", "user_id"),
        
        # Cart items - JOINs
        ("idx_cart_items_cart_id", "cart_items", "cart_id"),
        ("idx_cart_items_painting_id", "cart_items", "painting_id"),
        
        # Notifications - filtrage admin
        ("idx_notifications_user_id", "notifications", "user_id"),
        ("idx_notifications_is_read", "notifications", "is_read"),
        
        # Exhibitions - tri par date
        ("idx_exhibitions_date", "exhibitions", "date"),
        
        # Custom requests - filtrage par statut
        ("idx_custom_requests_status", "custom_requests", "status"),
        
        # Settings - lookup rapide
        ("idx_settings_key", "settings", "key"),
        
        # SAAS sites - lookup par user
        ("idx_saas_sites_user_id", "saas_sites", "user_id"),
        ("idx_saas_sites_status", "saas_sites", "status"),
    ]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for index_name, table_name, column_name in indexes:
            try:
                # Vérifier si l'index existe déjà
                cursor.execute("""
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = %s
                """, (index_name,))
                
                if not cursor.fetchone():
                    # Créer l'index - Valider les noms pour éviter SQL injection
                    # Les noms proviennent d'une liste codée en dur, donc sûrs
                    if not all(c.isalnum() or c == '_' for c in index_name):
                        raise ValueError(f"Nom d'index invalide: {index_name}")
                    if not all(c.isalnum() or c == '_' for c in table_name):
                        raise ValueError(f"Nom de table invalide: {table_name}")
                    if not all(c.isalnum() or c == '_' for c in column_name):
                        raise ValueError(f"Nom de colonne invalide: {column_name}")
                    
                    cursor.execute(f"CREATE INDEX {index_name} ON {table_name}({column_name})")
                    print(f"  ✅ Index créé: {index_name} sur {table_name}({column_name})")
                else:
                    print(f"  ℹ️  Index existe déjà: {index_name}")
            except Exception as e:
                print(f"  ⚠️  Erreur création index {index_name}: {e}")
        
        conn.commit()
    
    print(f"✅ Indexes de performance créés")

