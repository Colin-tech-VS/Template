"""
Database ou : Module de gestion de base de données Supabase/PostgreSQL
Migration complète depuis SQLite vers Supabase/Postgres
OPTIMISÉ: Connection pooling, logging de performance
"""

import os
from urllib.parse import urlparse
from contextlib import contextmanager
import time
import atexit
import logging
import threading

# ============================================================
# ✅ Multi-driver compatibility: psycopg3 → psycopg2 → pg8000
# ✅ Version corrigée, compatible Termux, PC, serveur
# ✅ Extras psycopg3 optionnels
# ✅ pg8000.dbapi conservé
# ============================================================

DRIVER = None

# --- Try psycopg3 (driver only) ---
try:
    import psycopg as psycopg3  # type: ignore
    DRIVER = "psycopg3"
except (ImportError, ModuleNotFoundError):
    psycopg3 = None

# --- Try psycopg2 ---
if DRIVER is None:
    try:
        import psycopg2
        import psycopg2.extras
        import psycopg2.pool
        DRIVER = "psycopg2"
    except (ImportError, ModuleNotFoundError):
        psycopg2 = None

# --- Final fallback: pg8000 ---
if DRIVER is None:
    try:
        import pg8000.dbapi
        DRIVER = "pg8000"
    except (ImportError, ModuleNotFoundError):
        pg8000 = None
        raise ImportError(
            "No PostgreSQL driver found. Please install one of:\n"
            "  - psycopg[binary]>=3.0.0 (recommended for PC/server)\n"
            "  - psycopg2-binary (alternative for PC/server)\n"
            "  - pg8000 (for Termux/Android or pure Python environments)"
        )

# --- Optional psycopg3 extras (pool, dict_row) ---
if DRIVER == "psycopg3":
    try:
        from psycopg_pool import ConnectionPool as PsycopgPool  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except Exception:
        PsycopgPool = None
        dict_row = None

# Legacy flag for backward compatibility
USING_PSYCOPG3 = (DRIVER == "psycopg3")

# Placeholder for PostgreSQL queries (all drivers use %s)
PARAM_PLACEHOLDER = '%s'

# PostgreSQL auto-increment type (SERIAL replaces SQLite's AUTOINCREMENT)
AUTOINCREMENT = 'SERIAL'

# Configuration du logging pour la performance
logging.basicConfig(level=logging.INFO)
perf_logger = logging.getLogger('db.performance')

# Configuration Supabase/PostgreSQL
DATABASE_URL = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("[WARNING] Aucune connexion PostgreSQL/Supabase configurée!")
    print("[WARNING] Définissez SUPABASE_DB_URL ou DATABASE_URL dans les variables d'environnement")
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
        'sslmode': 'require'
    }
    print(f"✅ Configuration Supabase/Postgres: {DB_CONFIG['host']}/{DB_CONFIG['database']}")
    print(f"✅ Using database driver: {DRIVER}")
except Exception as e:
    print(f"❌ Erreur parsing DATABASE_URL: {e}")
    raise

IS_POSTGRES = True

# =========================================
# CONNECTION POOL GLOBAL (OPTIMISATION)
# =========================================
CONNECTION_POOL = None

def init_connection_pool(minconn=1, maxconn=5):
    global CONNECTION_POOL

    if CONNECTION_POOL is not None:
        return CONNECTION_POOL

    try:
        if DRIVER == "psycopg3":
            if PsycopgPool:
                CONNECTION_POOL = PsycopgPool(conninfo=DATABASE_URL, min_size=minconn, max_size=maxconn)
                print(f"✅ psycopg ConnectionPool initialisé: {minconn}-{maxconn} connexions")
            else:
                print("⚠️ psycopg3 détecté mais psycopg_pool indisponible → pas de pooling")
                CONNECTION_POOL = None

        elif DRIVER == "psycopg2":
            CONNECTION_POOL = psycopg2.pool.ThreadedConnectionPool(
                minconn=minconn,
                maxconn=maxconn,
                **DB_CONFIG
            )
            print(f"✅ psycopg2 ThreadedConnectionPool initialisé: {minconn}-{maxconn} connexions")

        elif DRIVER == "pg8000":
            CONNECTION_POOL = {
                'connections': [],
                'min_size': minconn,
                'max_size': maxconn,
                'in_use': set(),
                'lock': threading.Lock()
            }
            print(f"✅ pg8000 simple pool initialisé: {minconn}-{maxconn} connexions")

        return CONNECTION_POOL

    except Exception as e:
        print(f"❌ Erreur initialisation connection pool: {e}")
        raise


def get_pool_connection():
    global CONNECTION_POOL

    if CONNECTION_POOL is None:
        init_connection_pool()

    if DRIVER == "psycopg3":
        raise RuntimeError("get_pool_connection() non supporté avec psycopg3")

    elif DRIVER == "psycopg2":
        try:
            return CONNECTION_POOL.getconn()
        except Exception as e:
            perf_logger.error(f"Erreur obtention connexion du pool: {e}")
            raise

    elif DRIVER == "pg8000":
        try:
            with CONNECTION_POOL['lock']:
                if CONNECTION_POOL['connections']:
                    conn = CONNECTION_POOL['connections'].pop(0)
                    CONNECTION_POOL['in_use'].add(id(conn))
                    return conn

                if len(CONNECTION_POOL['in_use']) < CONNECTION_POOL['max_size']:
                    conn = pg8000.dbapi.connect(**DB_CONFIG)
                    CONNECTION_POOL['in_use'].add(id(conn))
                    return conn

            conn = pg8000.dbapi.connect(**DB_CONFIG)
            return conn

        except Exception as e:
            perf_logger.error(f"Erreur obtention connexion pg8000: {e}")
            raise


def return_pool_connection(conn):
    global CONNECTION_POOL

    if CONNECTION_POOL is None or conn is None:
        return

    if DRIVER == "psycopg3":
        try:
            conn.close()
        except Exception:
            pass
        return

    elif DRIVER == "psycopg2":
        CONNECTION_POOL.putconn(conn)

    elif DRIVER == "pg8000":
        try:
            with CONNECTION_POOL['lock']:
                conn_id = id(conn)
                if conn_id in CONNECTION_POOL['in_use']:
                    CONNECTION_POOL['in_use'].remove(conn_id)
                    if len(CONNECTION_POOL['connections']) < CONNECTION_POOL['min_size']:
                        CONNECTION_POOL['connections'].append(conn)
                    else:
                        conn.close()
                else:
                    conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass


def close_connection_pool():
    global CONNECTION_POOL

    if CONNECTION_POOL is not None:
        try:
            if DRIVER == "psycopg3":
                try:
                    CONNECTION_POOL.close()
                except Exception:
                    pass
                try:
                    wait = getattr(CONNECTION_POOL, 'wait_closed', None)
                    if callable(wait):
                        wait(5.0)
                except Exception:
                    pass

            elif DRIVER == "psycopg2":
                try:
                    CONNECTION_POOL.closeall()
                except Exception:
                    pass

            elif DRIVER == "pg8000":
                try:
                    with CONNECTION_POOL['lock']:
                        for conn in CONNECTION_POOL['connections']:
                            try:
                                conn.close()
                            except Exception:
                                pass
                except Exception:
                    pass

        finally:
            CONNECTION_POOL = None
            print("✅ Connection pool fermé")


try:
    atexit.register(close_connection_pool)
except Exception:
    pass


class ConnectionWrapper:
    """
    Wrapper pour une connexion PostgreSQL/Supabase qui retourne automatiquement
    la connexion au pool lors du close()
    """

    def __init__(self, connection):
        connection_obj = connection
        release_func = None
        if isinstance(connection, tuple) and len(connection) == 2:
            connection_obj, release_func = connection

        object.__setattr__(self, '_connection', connection_obj)
        object.__setattr__(self, '_release_func', release_func)
        object.__setattr__(self, '_closed', False)

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def __setattr__(self, name, value):
        if name in ('_connection', '_closed'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._connection, name, value)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        if not self._closed:
            if getattr(self, '_release_func', None):
                try:
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
        return self._closed


@contextmanager
def get_db_connection():
    """
    Context manager pour obtenir une connexion Supabase/PostgreSQL
    OPTIMISÉ: Utilise le connection pool au lieu de créer une nouvelle connexion
    Supports psycopg3, psycopg2, and pg8000 drivers
    """
    start_time = time.time()

    if DRIVER == "psycopg3":
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
            try:
                ctx.__exit__(None, None, None)
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass

    elif DRIVER == "psycopg2":
        conn = get_pool_connection()
        conn_time = (time.time() - start_time) * 1000
        if conn_time > 10:
            perf_logger.warning(f"Connexion lente depuis le pool: {conn_time:.2f}ms")
        try:
            yield conn
        finally:
            return_pool_connection(conn)

    elif DRIVER == "pg8000":
        conn = get_pool_connection()
        conn_time = (time.time() - start_time) * 1000
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
    Supports psycopg3, psycopg2, and pg8000 drivers
    """
    start_time = time.time()

    if DRIVER == "psycopg3":
        if CONNECTION_POOL is None:
            init_connection_pool()
        ctx = CONNECTION_POOL.connection()
        conn = ctx.__enter__()
        try:
            if dict_row:
                conn.row_factory = dict_row
        except Exception:
            pass

        conn_time = (time.time() - start_time) * 1000
        if conn_time > 10:
            perf_logger.warning(f"get_db() lent: {conn_time:.2f}ms")

        return ConnectionWrapper((conn, ctx.__exit__))

    elif DRIVER == "psycopg2":
        conn = get_pool_connection()
        conn.cursor_factory = psycopg2.extras.RealDictCursor

        conn_time = (time.time() - start_time) * 1000
        if conn_time > 10:
            perf_logger.warning(f"get_db() lent: {conn_time:.2f}ms")

        return ConnectionWrapper(conn)

    elif DRIVER == "pg8000":
        conn = get_pool_connection()

        original_cursor = conn.cursor

        def cursor_with_dict_access():
            cur = original_cursor()
            original_fetchone = cur.fetchone
            original_fetchall = cur.fetchall

            def fetchone_dict():
                row = original_fetchone()
                if row is None:
                    return None
                if cur.description:
                    if not hasattr(cur, '_column_names'):
                        cur._column_names = [desc[0] for desc in cur.description]
                    return dict(zip(cur._column_names, row))
                return row

            def fetchall_dict():
                rows = original_fetchall()
                if not rows or not cur.description:
                    return rows
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in rows]

            cur.fetchone = fetchone_dict
            cur.fetchall = fetchall_dict
            return cur

        conn.cursor = cursor_with_dict_access

        conn_time = (time.time() - start_time) * 1000
        if conn_time > 10:
            perf_logger.warning(f"get_db() lent: {conn_time:.2f}ms")

        return ConnectionWrapper(conn)


def adapt_query(query):
    """
    Adapte une requête pour PostgreSQL/Supabase
    - Remplace les placeholders SQLite (?) par PostgreSQL (%s)
    - Gère les types de données spécifiques
    """
    query = query.replace('?', '%s')
    query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    query = query.replace('AUTOINCREMENT', '')
    return query


def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=True):
    """
    Exécute une requête PostgreSQL/Supabase avec gestion automatique de la connexion
    OPTIMISÉ: Utilise le connection pool et log les requêtes lentes
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

        if total_time > 100:
            truncated = adapted_query.replace("\n", " ")[:200]
            perf_logger.warning(
                f"⏱️ Requête lente ({total_time:.2f}ms) : {truncated}..."
            )

        return result