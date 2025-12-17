import os

# Fonction pour récupérer dynamiquement la clé Stripe depuis le dashboard central
def get_stripe_secret_key():
    # 1) env var (highest priority)
    env_key = os.getenv('STRIPE_SECRET_KEY') or os.getenv('STRIPE_API_KEY')
    if env_key:
        print('[SAAS] Stripe secret key loaded from environment')
        return env_key

    # 2) local DB setting
    try:
        db_key = get_setting('stripe_secret_key')
        if db_key:
            print('[SAAS] Stripe secret key loaded from local settings (DB)')
            return db_key
    except Exception as e:
        print(f"[SAAS] Erreur lecture clé Stripe BDD: {e}")

    # 3) dashboard server->server fallback (only if dashboard exposes it)
    try:
        base_url = get_setting("dashboard_api_base") or os.getenv('DASHBOARD_URL') or "https://admin.artworksdigital.fr"
        if base_url:
            url = f"{base_url.rstrip('/')}/api/export/settings/stripe_secret_key"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                key = data.get("stripe_secret_key") or data.get('secret_key') or data.get('sk')
                if key:
                    print('[SAAS] Stripe secret key retrieved from dashboard endpoint')
                    return key
    except Exception as e:
        print(f"[SAAS] Erreur récupération clé Stripe dashboard: {e}")

    return None


# In-memory settings cache (simple TTL)
SETTINGS_CACHE = {}
# TTL in seconds for cached settings
SETTINGS_CACHE_TTL = int(os.getenv('SETTINGS_CACHE_TTL', '300'))

def invalidate_all_settings_cache():
    SETTINGS_CACHE.clear()
# --------------------------------
# IMPORTS
# --------------------------------
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, send_file, abort, jsonify, has_request_context
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from functools import wraps
import os
import time
from jinja2 import FileSystemLoader, ChoiceLoader
import smtplib
import uuid
import secrets
import tempfile
import stripe
import json
import requests
import urllib.parse
import hmac
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from flask_mail import Mail
from openpyxl import Workbook
from io import BytesIO
from dotenv import load_dotenv
from PIL import Image

# Charger les variables d'environnement depuis .env
load_dotenv()

# Import du module de base de données
from database import (
    get_db, 
    get_db_connection, 
    execute_query, 
    create_table_if_not_exists,
    add_column_if_not_exists,
    adapt_query,
    init_database,
    IS_POSTGRES,
    PARAM_PLACEHOLDER
)


# --------------------------------
# CONFIGURATION
# --------------------------------

# Clé API maître pour le dashboard (depuis variable d'environnement Scalingo)
TEMPLATE_MASTER_API_KEY = os.getenv('TEMPLATE_MASTER_API_KEY')
if TEMPLATE_MASTER_API_KEY:
    try:
        print("🔑 Configuration sécurisée chargée avec succès")
    except UnicodeEncodeError:
        print("[KEY] Configuration securisee chargee avec succes")
else:
    try:
        print("⚠️ ATTENTION: Configuration d'authentification manquante")
        print("⚠️ TEMPLATE_MASTER_API_KEY non définie - génération d'une clé temporaire")
        print("⚠️ En production, définissez TOUJOURS TEMPLATE_MASTER_API_KEY dans les variables d'environnement")
    except UnicodeEncodeError:
        print("[WARNING] Configuration d'authentification manquante")
        print("[WARNING] TEMPLATE_MASTER_API_KEY non definie")
        print("[WARNING] En production, definissez TEMPLATE_MASTER_API_KEY dans les variables d'environnement")
    # Generate a secure random key for development
    # This prevents timing attacks while still requiring explicit configuration
    TEMPLATE_MASTER_API_KEY = secrets.token_urlsafe(32)

# Dummy value for constant-time comparisons when keys are missing
# This avoids generating random values on every comparison
_DUMMY_KEY_FOR_COMPARISON = secrets.token_urlsafe(32)

app = Flask(__name__)
app.secret_key = 'secret_key'

# Config Flask-Mail
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='coco.cayre@example.com',
    MAIL_PASSWORD='psgk wjhd wbdj gduo'
)
mail = Mail(app)

# Per-site templates: if `templates/sites/<slug>/` exists, use it first then fallback to default templates/
@app.before_request
def select_site_template_loader():
    try:
        host = request.host.split(':')[0].lower()
        # sanitize host into a folder-friendly slug
        slug = secure_filename(host).replace('-', '_')
        site_templates_dir = os.path.join(app.root_path, 'templates', 'sites', slug)
        default_templates_dir = os.path.join(app.root_path, 'templates')
        if os.path.isdir(site_templates_dir):
            app.jinja_loader = ChoiceLoader([
                FileSystemLoader(site_templates_dir),
                FileSystemLoader(default_templates_dir)
            ])
        else:
            # ensure default loader
            app.jinja_loader = FileSystemLoader(default_templates_dir)
    except Exception:
        # if anything goes wrong, leave loader as default
        pass

# --- Performance: optional HTTP compression (Flask-Compress) ---
try:
    from flask_compress import Compress
    Compress(app)
    print('[PERF] Flask-Compress enabled')
except Exception as _e:
    print('[PERF] Flask-Compress not enabled (package missing or init error)')


# Add caching headers for static assets to reduce repeat downloads
@app.after_request
def set_static_cache_headers(response):
    try:
        # Only for successful GETs to the static folder
        if request.method == 'GET' and request.path.startswith('/static/') and response.status_code == 200:
            # Only set if not already present
            if 'Cache-Control' not in response.headers:
                # long cache for static files — update filenames on deploy to bust cache
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    except Exception:
        pass
    return response

# Dossiers de stockage
app.config['UPLOAD_FOLDER'] = 'static/Images'        # pour les peintures
app.config['EXPO_UPLOAD_FOLDER'] = 'static/expo_images'  # pour les exhibitions

# Extensions autorisées (communes aux deux)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Vérification d'extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Helper: save uploaded file and create a WebP version; return DB path (optionally prefixed)
def save_image_and_convert_to_webp(file, dest_folder, db_prefix=None, quality=80):
    """Save uploaded file to dest_folder and write a .webp copy.
    If db_prefix is provided, return f"{db_prefix}/{base}.webp", else return base.webp filename.
    """
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base = f"{name}_{timestamp}"
    os.makedirs(dest_folder, exist_ok=True)
    original_path = os.path.join(dest_folder, f"{base}{ext}")
    file.save(original_path)

    try:
        img = Image.open(original_path)
        # Convert RGBA -> RGB for WebP compatibility when necessary
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        else:
            img = img.convert("RGB")

        webp_name = f"{base}.webp"
        webp_path = os.path.join(dest_folder, webp_name)
        img.save(webp_path, "WEBP", quality=quality, method=6)
    except Exception:
        # If conversion fails, fall back to original filename
        webp_name = f"{base}{ext}"

    if db_prefix:
        return f"{db_prefix}/{webp_name}"
    return webp_name


def get_order_by_id(order_id):
    """Récupère une commande par ID - OPTIMISÉ: colonnes spécifiques"""
    conn = get_db()
    cursor = conn.cursor()
    query = adapt_query("""
        SELECT id, customer_name, email, address, total_price, order_date, status, user_id
        FROM orders 
        WHERE id = %s
    """)
    cursor.execute(query, (order_id,))
    order = cursor.fetchone()
    conn.close()
    return order

def get_order_items(order_id):
    """Récupère les items d'une commande - OPTIMISÉ: colonnes spécifiques"""
    conn = get_db()
    cursor = conn.cursor()
    query = adapt_query("""
        SELECT id, order_id, painting_id, quantity, price
        FROM order_items 
        WHERE order_id = %s
    """)
    cursor.execute(query, (order_id,))
    items = cursor.fetchall()
    conn.close()
    return items

# --------------------------------
# FONCTION GÉNÉRATION EMAIL HTML
# --------------------------------
def generate_email_html(title, content, button_text=None, button_url=None):
    """Génère un template d'email HTML avec les couleurs du site"""
    # Récupérer les couleurs du site
    color_primary = get_setting("color_primary") or "#6366f1"
    color_secondary = get_setting("color_secondary") or "#8b5cf6"
    site_name = get_setting("site_name") or "JB Art"
    site_logo = get_setting("site_logo") or "🎨 JB Art"
    
    button_html = ""
    if button_text and button_url:
        button_html = f"""
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin: 30px 0;">
            <tr>
                <td style="border-radius: 50px; background: linear-gradient(135deg, {color_primary} 0%, {color_secondary} 100%);">
                    <a href="{button_url}" target="_blank" style="
                        display: inline-block;
                        padding: 16px 40px;
                        font-size: 16px;
                        color: #ffffff;
                        text-decoration: none;
                        font-weight: 700;
                        letter-spacing: 0.5px;
                        border-radius: 50px;
                    ">{button_text}</a>
                </td>
            </tr>
        </table>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
        </style>
    </head>
    <body style="
        margin: 0;
        padding: 0;
        font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: linear-gradient(135deg, {color_primary} 0%, {color_secondary} 100%);
        padding: 40px 20px;
    ">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="
            max-width: 600px;
            width: 100%;
            background: rgba(255, 255, 255, 0.98);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        ">
            <!-- HEADER -->
            <tr>
                <td style="
                    background: linear-gradient(135deg, {color_primary} 0%, {color_secondary} 100%);
                    padding: 40px 30px;
                    text-align: center;
                ">
                    <h1 style="
                        margin: 0;
                        color: #ffffff;
                        font-size: 32px;
                        font-weight: 800;
                        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    ">{site_logo}</h1>
                </td>
            </tr>
            
            <!-- CONTENT -->
            <tr>
                <td style="padding: 40px 30px;">
                    <h2 style="
                        margin: 0 0 20px 0;
                        color: #1a1a1a;
                        font-size: 24px;
                        font-weight: 700;
                    ">{title}</h2>
                    
                    <div style="
                        color: #444;
                        font-size: 15px;
                        line-height: 1.8;
                    ">
                        {content}
                    </div>
                    
                    {button_html}
                </td>
            </tr>
            
            <!-- FOOTER -->
            <tr>
                <td style="
                    background: #f8f9fa;
                    padding: 30px;
                    text-align: center;
                    border-top: 1px solid #e0e0e0;
                ">
                    <p style="
                        margin: 0 0 10px 0;
                        color: #666;
                        font-size: 14px;
                    ">Cordialement,<br><strong>{site_name}</strong></p>
                    
                    <p style="
                        margin: 0;
                        color: #999;
                        font-size: 12px;
                    ">Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

TABLES = {
    # Table tenants pour l'isolation multi-tenant
    "tenants": {
        "id": "SERIAL PRIMARY KEY",
        "host": "TEXT UNIQUE NOT NULL",
        "name": "TEXT",
        "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
    },
    "users": {
        "id": "SERIAL PRIMARY KEY",
        "name": "TEXT NOT NULL",
        "email": "TEXT NOT NULL",
        "password": "TEXT NOT NULL",
        "create_date": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "role": "TEXT DEFAULT 'user'",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    "paintings": {
        "id": "SERIAL PRIMARY KEY",
        "name": "TEXT NOT NULL",
        "image": "TEXT NOT NULL",
        "price": "REAL NOT NULL DEFAULT 0",
        "quantity": "INTEGER NOT NULL DEFAULT 0",
        "create_date": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "description": "TEXT",
        "description_long": "TEXT",
        "dimensions": "TEXT",
        "technique": "TEXT",
        "year": "TEXT",
        "category": "TEXT",
        "status": "TEXT DEFAULT 'disponible'",
        "image_2": "TEXT",
        "image_3": "TEXT",
        "image_4": "TEXT",
        "weight": "TEXT",
        "framed": "INTEGER DEFAULT 0",
        "certificate": "INTEGER DEFAULT 1",
        "unique_piece": "INTEGER DEFAULT 1",
        "display_order": "INTEGER DEFAULT 0",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    "orders": {
        "id": "SERIAL PRIMARY KEY",
        "customer_name": "TEXT NOT NULL",
        "email": "TEXT NOT NULL",
        "address": "TEXT NOT NULL DEFAULT ''",
        "total_price": "REAL NOT NULL DEFAULT 0",
        "order_date": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "status": "TEXT NOT NULL DEFAULT 'En cours'",
        "user_id": "INTEGER",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    "order_items": {
        "id": "SERIAL PRIMARY KEY",
        "order_id": "INTEGER NOT NULL",
        "painting_id": "INTEGER NOT NULL",
        "quantity": "INTEGER NOT NULL",
        "price": "REAL NOT NULL",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    "cart_items": {
        "id": "SERIAL PRIMARY KEY",
        "cart_id": "INTEGER NOT NULL",
        "painting_id": "INTEGER NOT NULL",
        "quantity": "INTEGER NOT NULL",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    "carts": {
        "id": "SERIAL PRIMARY KEY",
        "session_id": "TEXT NOT NULL UNIQUE",
        "user_id": "INTEGER",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    "favorites": {
        "id": "SERIAL PRIMARY KEY",
        "user_id": "INTEGER NOT NULL",
        "painting_id": "INTEGER NOT NULL",
        "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    "notifications": {
        "id": "SERIAL PRIMARY KEY",
        "user_id": "INTEGER",
        "message": "TEXT NOT NULL",
        "type": "TEXT NOT NULL",
        "url": "TEXT",
        "is_read": "INTEGER NOT NULL DEFAULT 0",
        "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    "exhibitions": {
        "id": "SERIAL PRIMARY KEY",
        "title": "TEXT NOT NULL",
        "location": "TEXT NOT NULL",
        "date": "TEXT NOT NULL",
        "start_time": "TEXT",
        "end_time": "TEXT",
        "description": "TEXT",
        "venue_details": "TEXT",
        "organizer": "TEXT",
        "entry_price": "TEXT",
        "contact_info": "TEXT",
        "image": "TEXT",
        "create_date": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    "custom_requests": {
        "id": "SERIAL PRIMARY KEY",
        "client_name": "TEXT NOT NULL",
        "client_email": "TEXT NOT NULL",
        "client_phone": "TEXT",
        "project_type": "TEXT NOT NULL",
        "description": "TEXT NOT NULL",
        "budget": "TEXT",
        "dimensions": "TEXT",
        "deadline": "TEXT",
        "reference_images": "TEXT",
        "status": "TEXT NOT NULL DEFAULT 'En attente'",
        "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "admin_notes": "TEXT",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    # Nouvelle table settings pour stocker toutes les clés API et configs
    "settings": {
        "id": "SERIAL PRIMARY KEY",
        "key": "TEXT NOT NULL",
        "value": "TEXT NOT NULL",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    "stripe_events": {
        "id": "TEXT PRIMARY KEY",
        "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    },
    # Table SAAS: suivi du cycle de vie des sites artistes
    "saas_sites": {
        "id": "SERIAL PRIMARY KEY",
        "user_id": "INTEGER UNIQUE",
        "status": "TEXT NOT NULL DEFAULT 'pending_approval'",
        "sandbox_url": "TEXT",
        "final_domain": "TEXT",
        "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "tenant_id": "INTEGER NOT NULL DEFAULT 1"
    }
}

def get_user_id():
    """Récupère le user_id depuis la session Flask"""
    return session.get('user_id')


def safe_row_get(row, key, index=0, default=None):
    """Retourne une valeur depuis un résultat de curseur quel que soit le type.
    Supporte tuple/list (index), dict (key), sqlite3.Row (mapping access) ou objets avec .get().
    """
    if row is None:
        return default
    try:
        if isinstance(row, (list, tuple)):
            return row[index]
        if isinstance(row, dict):
            return row.get(key, default)
        # sqlite3.Row supports mapping access but not get()
        if hasattr(row, 'get'):
            return row.get(key, default)
        try:
            return row[key]
        except Exception:
            return default
    except Exception:
        return default

def convert_rows_to_dicts(rows, cur_description):
    """Convert database rows to list of dicts, handling both RealDictRow and tuple types.
    
    Args:
        rows: List of row objects from fetchall()
        cur_description: Cursor description for column names
    
    Returns:
        List of dictionaries
    """
    if not rows:
        return []
    
    result = []
    columns = None
    
    for row in rows:
        if hasattr(row, 'get'):
            # RealDictRow or dict-like object
            result.append(dict(row))
        else:
            # Tuple - need column names
            if columns is None:
                columns = [description[0] for description in cur_description]
            result.append(dict(zip(columns, row)))
    
    return result

def get_setting(key, user_id=None):
    """
    Récupère une clé de paramètre
    Args:
        key: Clé du paramètre
        user_id: ID de l'utilisateur/site. Si None, utilise la DB centrale
    """
    # Simple in-process TTL cache to reduce DB reads for frequently requested settings
    cache_key = (key, user_id)
    now = time.time()
    cache_entry = SETTINGS_CACHE.get(cache_key)
    if cache_entry:
        value, expires_at = cache_entry
        if now < expires_at:
            return value
        else:
            # expired
            try:
                del SETTINGS_CACHE[cache_key]
            except KeyError:
                pass

    conn = get_db(user_id=user_id)
    cur = conn.cursor()
    query = adapt_query("SELECT value FROM settings WHERE key = ?")
    cur.execute(query, (key,))
    row = cur.fetchone()
    conn.close()
    if row:
        val = row['value'] if IS_POSTGRES else row["value"]
        # store in cache for a short TTL
        SETTINGS_CACHE[cache_key] = (val, now + SETTINGS_CACHE_TTL)
        return val
    return None

# Charger la clé Stripe de manière lazy (depuis env var en priorité pour éviter les connexions au démarrage)
stripe_key = os.getenv('STRIPE_SECRET_KEY') or os.getenv('STRIPE_API_KEY')

if not stripe_key:
    # Fallback: essayer de charger depuis la BD (mais avec gestion d'erreur)
    try:
        stripe_key = get_stripe_secret_key()
    except Exception as e:
        print(f"[STARTUP] ⚠️  Erreur lecture clé Stripe: {e}")
        stripe_key = None

masked_stripe = (stripe_key[:6] + "…") if stripe_key else "None"
print("Clé Stripe actuelle (masquée) :", masked_stripe)
# Configurer Stripe si la clé est disponible (secret côté serveur)
if stripe_key:
    try:
        stripe.api_key = stripe_key
    except Exception as e:
        print(f"[SAAS] Erreur configuration Stripe API key: {e}")
else:
    print("Stripe non configuré: aucune clé fournie")

# Vérifier les valeurs SMTP (charger de manière LAZY depuis les env vars ou la BD)
# Au lieu de charger au démarrage, on utilise des variables d'environnement avec fallback
def get_smtp_config():
    """Charger SMTP de manière lazy depuis env vars ou BD"""
    return {
        'server': os.getenv("SMTP_SERVER") or "smtp.gmail.com",
        'port': int(os.getenv("SMTP_PORT") or 587),
        'user': os.getenv("SMTP_USER") or "coco.cayre@gmail.com",
        'password': os.getenv("SMTP_PASSWORD") or "motdepassepardefaut"
    }

smtp_config = get_smtp_config()
smtp_server = smtp_config['server']
smtp_port = smtp_config['port']
smtp_user = smtp_config['user']
smtp_password = smtp_config['password']

print("SMTP_SERVER :", smtp_server)
print("SMTP_PORT   :", smtp_port)
print("SMTP_USER   :", smtp_user)
print("SMTP_PASSWORD défini :", bool(smtp_password))

google_places_key = os.getenv("GOOGLE_PLACES_KEY") or "CLE_PAR_DEFAUT"
print("Google Places Key utilisée :", google_places_key)



def set_setting(key, value, user_id=None):
    """
    Met à jour ou crée une clé de paramètre
    Args:
        key: Clé du paramètre
        value: Valeur du paramètre
        user_id: ID de l'utilisateur/site. Si None, utilise la DB centrale
    """
    # Détection dynamique de la colonne tenant_id (cache pour perf)
    if not hasattr(set_setting, '_has_tenant_id'):
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM settings LIMIT 1")
            colnames = [desc[0] for desc in cur.description]
            set_setting._has_tenant_id = 'tenant_id' in colnames
        except Exception:
            set_setting._has_tenant_id = False
        finally:
            conn.close()
    has_tenant_id = getattr(set_setting, '_has_tenant_id', False)

    conn = get_db(user_id=user_id)
    cur = conn.cursor()
    try:
        if user_id is not None and has_tenant_id:
            query = adapt_query("""
                INSERT INTO settings (key, value, tenant_id) VALUES (?, ?, ?)
                ON CONFLICT(key, tenant_id) DO UPDATE SET value=excluded.value
            """)
            cur.execute(query, (key, value, user_id))
        else:
            # Fallback: use default tenant_id = 1 if tenant_id column exists
            # This ensures compatibility with the UNIQUE constraint on (key, tenant_id)
            if has_tenant_id:
                query = adapt_query("""
                    INSERT INTO settings (key, value, tenant_id) VALUES (?, ?, ?)
                    ON CONFLICT(key, tenant_id) DO UPDATE SET value=excluded.value
                """)
                cur.execute(query, (key, value, 1))
            else:
                # Legacy mode for databases without tenant_id column
                query = adapt_query("""
                    INSERT INTO settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """)
                cur.execute(query, (key, value))
        conn.commit()
    finally:
        conn.close()
    # Invalidate cache for this setting
    try:
        SETTINGS_CACHE.pop((key, user_id), None)
    except Exception:
        pass


# Prévisualisation / Dashboard helpers
def get_dashboard_base_url():
    return (get_setting("dashboard_api_base") or "https://admin.artworksdigital.fr").rstrip("/")


def is_preview_request():
    host = (request.host or "").lower()
    return (
        host.startswith("preview-")
        or ".preview." in host
        or host.startswith("preview.")
        or "sandbox" in host
    )


def get_current_tenant_id():
    """
    Récupère le tenant_id du tenant courant basé sur le host de la requête.
    Retourne 1 par défaut si aucun tenant n'est trouvé (tenant par défaut).
    MULTI-TENANT: Isolation stricte des données par tenant.
    
    NOTE: Cette fonction doit être appelée uniquement dans un contexte de requête HTTP.
    Si appelée hors contexte (ex: au démarrage), retourne le tenant par défaut (1).
    """
    # Vérifier qu'on est dans un contexte de requête HTTP
    if not has_request_context():
        print(f"[TENANT] get_current_tenant_id() appelé hors contexte HTTP - utilisation du tenant par défaut (1)")
        return 1
    
    try:
        host = request.host.split(':')[0].lower()
        conn = get_db()
        cur = conn.cursor()
        cur.execute(adapt_query("SELECT id FROM tenants WHERE host = ?"), (host,))
        result = cur.fetchone()
        conn.close()
        if result:
            return safe_row_get(result, 'id', index=0, default=1)
        # Si aucun tenant trouvé, retourner le tenant par défaut (id=1)
        return 1
    except Exception as e:
        print(f"[TENANT] Erreur récupération tenant_id: {e}")
        # En cas d'erreur, retourner le tenant par défaut
        return 1


def fetch_dashboard_site_price():
    base_url = get_dashboard_base_url()
    site_id = get_setting("dashboard_id")

    # Priorité 0: override manuel (settings)
    manual = get_setting("saas_site_price_override")
    try:
        if manual:
            val = float(manual)
            if val > 0:
                return val
    except Exception:
        pass

    # Priorité 1: endpoint price dédié au site
    endpoint_site_price = f"{base_url}/api/sites/{site_id}/price" if site_id else f"{base_url}/api/sites/price"
    # Priorité 2: endpoint config (prix affiché dans l'input config artwork)
    endpoint_config = f"{base_url}/api/config/artworks"
    endpoint_config_alt = f"{base_url}/api/config/artwork"

    endpoints = [endpoint_site_price, endpoint_config, endpoint_config_alt]
    try:
        for ep in endpoints:
            try:
                resp = requests.get(ep, timeout=8)
            except Exception:
                # network error, try next endpoint
                continue
            if resp.status_code != 200:
                continue
            data = resp.json() or {}
            base_price = float(data.get("price") or data.get("site_price") or 0)
            if base_price > 0:
                set_setting("saas_site_price_cache", str(base_price))
                return base_price
            # Non-fatal: endpoint responded but did not contain a usable price
            print(f"[SAAS] Prix non disponible dans la réponse depuis {ep}: {data}")
    except Exception as e:
        print(f"[SAAS] Erreur récupération prix dashboard: {e}")

    # Fallback: use cached value if present
    cached = get_setting("saas_site_price_cache")
    if cached:
        try:
            val = float(cached)
            print(f"[SAAS] Utilisation du cache saas_site_price_cache: {val}")
            return val
        except Exception:
            pass

    # No price available
    print(f"[SAAS] Aucun prix récupérable (endpoints et cache vides)")
    return None


# ----------------------------
# API for dashboard -> template
# ----------------------------
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "invalid_api_key", "success": False}), 401
        
        expected_master = TEMPLATE_MASTER_API_KEY

        # allow either master key or stored export_api_key (if set)
        stored = None
        try:
            stored = get_setting('export_api_key')
        except Exception:
            stored = None

        ok_master = False
        ok_stored = False
        
        # Check master key with constant-time comparison
        # Always perform comparison to prevent timing leaks
        if expected_master:
            try:
                ok_master = hmac.compare_digest(api_key, expected_master)
            except Exception:
                ok_master = False
        else:
            # Use dummy comparison to maintain constant timing
            try:
                _ = hmac.compare_digest(api_key, _DUMMY_KEY_FOR_COMPARISON)
            except Exception:
                pass
            ok_master = False
        
        # Check stored key with constant-time comparison
        # Always perform comparison to prevent timing leaks
        if stored:
            try:
                ok_stored = hmac.compare_digest(api_key, stored)
            except Exception:
                ok_stored = False
        else:
            # Use dummy comparison to maintain constant timing
            try:
                _ = hmac.compare_digest(api_key, _DUMMY_KEY_FOR_COMPARISON)
            except Exception:
                pass
            ok_stored = False

        if not (ok_master or ok_stored):
            return jsonify({"error": "invalid_api_key", "success": False}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/api/export/settings/<key>', methods=['PUT'])
@require_api_key
def api_put_setting(key):
    """PUT per-key setting. Body: {"value": "..."}
    Protected by X-API-Key header.
    """
    data = request.get_json(silent=True) or {}
    value = data.get('value')
    if value is None:
        return jsonify({"error": "Missing value"}), 400
    try:
        set_setting(key, value)
        return jsonify({"ok": True, "key": key}), 200
    except Exception as e:
        print(f"[API] Error saving setting {key}: {e}")
        return jsonify({"error": "internal"}), 500


@app.route('/api/export/settings', methods=['GET'])
def api_get_settings():
    """Return all settings as a dict. If caller provides valid X-API-Key, returns secrets too.
    Otherwise, sensitive keys (stripe secret) are omitted.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings")
    rows = cur.fetchall()
    result = {}
    for r in rows:
        k = safe_row_get(r, 'key', index=0)
        v = safe_row_get(r, 'value', index=1)
        result[k] = v
    conn.close()

    # Ensure stripe_secret_key is never exposed via this endpoint
    if 'stripe_secret_key' in result:
        result.pop('stripe_secret_key')

    # Filter other sensitive values unless correct API key provided
    api_key = request.headers.get('X-API-Key')
    master_key = TEMPLATE_MASTER_API_KEY
    
    # Use constant-time comparison - always compare to prevent timing leaks
    has_valid_master = False
    if api_key and master_key:
        try:
            has_valid_master = hmac.compare_digest(api_key, master_key)
        except Exception:
            has_valid_master = False
    
    if not has_valid_master:
        filtered = {k: v for k, v in result.items() if not (k.lower().startswith('stripe') and ('secret' in k.lower() or 'sk_' in str(v)))}
        # Ensure publishable key stays available
        return jsonify(filtered)
    return jsonify(result)


@app.route('/api/template/config', methods=['GET'])
def api_template_config():
    """Expose la configuration utile du template: price, options, etc.
    This is intentionally public for the dashboard to read.
    """
    config = {
        "price": fetch_dashboard_site_price(),
        "site_name": get_setting('site_name'),
        "site_logo": get_setting('site_logo'),
        "options": {
            "enable_custom_orders": get_setting('enable_custom_orders') or '0'
        }
    }
    return jsonify(config)


@app.route('/api/sites/<site_name>/stripe-key', methods=['GET'])
def api_fallback_stripe_key(site_name):
    """Fallback: fetch stripe key from dashboard for a given site name.
    Server->server request uses TEMPLATE_MASTER_API_KEY if available.
    """
    try:
        base = get_dashboard_base_url()
        url = f"{base}/api/sites/{urllib.parse.quote_plus(site_name)}/stripe-key"
        headers = {}
        if TEMPLATE_MASTER_API_KEY:
            headers['X-API-Key'] = TEMPLATE_MASTER_API_KEY
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            return jsonify(resp.json()), 200
        return jsonify({"error": "not_found", "status": resp.status_code}), resp.status_code
    except Exception as e:
        print(f"[FALLBACK] Error fetching stripe key from dashboard: {e}")
        return jsonify({"error": "internal"}), 500


# ----------------------------
# Stripe webhook endpoint
# ----------------------------
@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET') or get_setting('stripe_webhook_secret')
    if not webhook_secret:
        print('[WEBHOOK] No webhook secret configured')
        return jsonify({'error': 'webhook not configured'}), 500
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        print(f"[WEBHOOK] Signature verification failed: {e}")
        return jsonify({'error': 'invalid signature'}), 400

    # Handle the event
    print(f"[WEBHOOK] Received event: {event['type']}")
    try:
        if event['type'] == 'checkout.session.completed':
            session_obj = event['data']['object']
            # Example: mark site active if metadata contains site_id
            site_id = session_obj.get('metadata', {}).get('site_id')
            if site_id:
                set_setting(f"site_{site_id}_active", '1')
                print(f"[WEBHOOK] Activated site {site_id}")
        elif event['type'] == 'invoice.paid':
            inv = event['data']['object']
            # handle invoice paid
            print('[WEBHOOK] invoice.paid handled')
        # add more event handling as needed
    except Exception as e:
        print(f"[WEBHOOK] Error processing event: {e}")

    return jsonify({'received': True}), 200

# Fonction helper pour récupérer le nombre de notifications non lues
def get_new_notifications_count():
    """Retourne le nombre de notifications admin non lues"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) as count
        FROM notifications 
        WHERE user_id IS NULL AND is_read = 0
    """)
    result = c.fetchone()
    count = safe_row_get(result, 'count', index=0, default=0)
    conn.close()
    return count

# Les fonctions create_table_if_not_exists et add_column_if_not_exists 
# sont maintenant dans database.py

def migrate_db():
    """Migration complète : crée tables puis ajoute colonnes manquantes"""
    # --- Créer toutes les tables si elles n'existent pas ---
    for table_name, cols in TABLES.items():
        create_table_if_not_exists(table_name, cols)
    
    # --- Ajouter les colonnes manquantes ---
    for table_name, cols in TABLES.items():
        for col_name, col_type in cols.items():
            add_column_if_not_exists(table_name, col_name, col_type)
    
    # --- Add UNIQUE constraint on settings(key, tenant_id) ---
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Check if constraint already exists
        cur.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'settings' 
            AND constraint_type = 'UNIQUE'
            AND constraint_name = 'settings_key_tenant_id_unique'
        """)
        
        constraint_exists = cur.fetchone() is not None
        
        if not constraint_exists:
            # First, remove duplicates keeping the most recent (highest id)
            duplicate_removal_success = True
            try:
                cur.execute("""
                    DELETE FROM settings a USING settings b
                    WHERE a.id < b.id 
                    AND a.key = b.key 
                    AND a.tenant_id = b.tenant_id
                """)
                deleted_count = cur.rowcount
                conn.commit()
                if deleted_count > 0:
                    print(f"✅ {deleted_count} duplicate(s) removed from settings")
            except Exception as e:
                print(f"⚠️  Error removing duplicates: {e}")
                conn.rollback()
                duplicate_removal_success = False
            
            # Add the UNIQUE constraint only if duplicate removal succeeded
            if duplicate_removal_success:
                try:
                    cur.execute("""
                        ALTER TABLE settings 
                        ADD CONSTRAINT settings_key_tenant_id_unique 
                        UNIQUE (key, tenant_id)
                    """)
                    conn.commit()
                    print("✅ UNIQUE constraint added on settings(key, tenant_id)")
                except Exception as e:
                    print(f"⚠️  Error adding UNIQUE constraint: {e}")
                    conn.rollback()
            else:
                print("⚠️  Skipping UNIQUE constraint creation due to duplicate removal failure")
        else:
            print("ℹ️  UNIQUE constraint on settings(key, tenant_id) already exists")
    except Exception as e:
        print(f"⚠️  Error in settings constraint migration: {e}")
    finally:
        # Ensure connection is always closed
        if conn is not None:
            try:
                conn.close()
            except:
                pass
    
    try:
        print("Migration terminée: OK")
    except UnicodeEncodeError:
        print("Migration terminée: OK (unicode fallback)")
    
    # --- Activer l'auto-registration par défaut ---
    if not get_setting("enable_auto_registration"):
        set_setting("enable_auto_registration", "true")
        try:
            print("Auto-registration activé par défaut")
        except UnicodeEncodeError:
            print("Auto-registration activé par défaut (unicode fallback)")



def generate_invoice_pdf(order, items, total_price):
    # Extract order fields safely using safe_row_get
    order_id = safe_row_get(order, 'id', index=0)
    customer_name = safe_row_get(order, 'customer_name', index=1)
    email = safe_row_get(order, 'email', index=2)
    address = safe_row_get(order, 'address', index=3)
    order_date = safe_row_get(order, 'order_date', index=5)
    
    file_path = f"temp_invoice_{order_id}.pdf"
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # Titre
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, f"Facture #{order_id}")

    # Infos client
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 90, f"Nom: {customer_name}")
    c.drawString(50, height - 110, f"Email: {email}")
    c.drawString(50, height - 130, f"Adresse: {address}")
    c.drawString(50, height - 150, f"Date: {order_date}")

    # Table des articles
    y = height - 190
    c.drawString(50, y, "Articles:")
    y -= 20
    for item in items:
        item_name = safe_row_get(item, 'name', index=1)
        item_quantity = safe_row_get(item, 'quantity', index=4)
        item_price = safe_row_get(item, 'price', index=3)
        c.drawString(60, y, f"{item_name} x {item_quantity} - {item_price} €")
        y -= 20

    # Total
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y-20, f"Total: {total_price} €")

    c.save()
    return file_path


def migrate_orders_db():
    """Migration des colonnes manquantes pour orders (DEPRECATED - utilisez migrate_db())"""
    # Cette fonction n'est plus nécessaire car migrate_db() gère tout
    pass

def get_or_create_cart(conn=None):
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True
    c = conn.cursor()

    session_id = request.cookies.get('cart_session')
    if not session_id:
        session_id = str(uuid.uuid4())
        # MULTI-TENANT: Inclure tenant_id dans INSERT
        c.execute(adapt_query("INSERT INTO carts (session_id, tenant_id) VALUES (?, ?)"), (session_id, tenant_id))
    else:
        # MULTI-TENANT: Filtrer par tenant_id
        c.execute(adapt_query("SELECT id FROM carts WHERE session_id=? AND tenant_id=?"), (session_id, tenant_id))
        if not c.fetchone():
            # MULTI-TENANT: Inclure tenant_id dans INSERT
            c.execute(adapt_query("INSERT INTO carts (session_id, tenant_id) VALUES (?, ?)"), (session_id, tenant_id))

    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT id FROM carts WHERE session_id=? AND tenant_id=?"), (session_id, tenant_id))
    cart_result = c.fetchone()
    cart_id = safe_row_get(cart_result, 'id', index=0)

    user_id = session.get("user_id")
    if user_id:
        # MULTI-TENANT: Ajouter tenant_id au WHERE
        c.execute(adapt_query("UPDATE carts SET user_id=? WHERE id=? AND tenant_id=?"), (user_id, cart_id, tenant_id))

    if close_conn:
        conn.close()

    return cart_id, session_id


# ===== FONCTIONS OBSOLÈTES (remplacées par migrate_db()) =====
def init_users_table():
    """DEPRECATED - utilisez migrate_db()"""
    pass

def migrate_orders_user():
    """DEPRECATED - utilisez migrate_db()"""
    pass

def migrate_users_role():
    """DEPRECATED - utilisez migrate_db()"""
    pass

def init_favorites_table():
    """DEPRECATED - utilisez migrate_db()"""
    pass
# ==============================================================

def set_admin_user(email):
    """Définit un utilisateur comme administrateur"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    try:
        from database import add_column_if_not_exists
        add_column_if_not_exists('users', 'role', 'TEXT DEFAULT "user"')
        
        # MULTI-TENANT: Ajouter tenant_id au WHERE
        query = adapt_query("UPDATE users SET role='admin' WHERE email=? AND tenant_id=?")
        c.execute(query, (email, tenant_id))
        conn.commit()
        print(f"L'utilisateur {email} est maintenant administrateur")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        conn.close()

def merge_carts(user_id, session_id):
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()

    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT id FROM carts WHERE user_id=? AND tenant_id=?"), (user_id, tenant_id))
    user_cart = c.fetchone()
    c.execute(adapt_query("SELECT id FROM carts WHERE session_id=? AND tenant_id=?"), (session_id, tenant_id))
    session_cart = c.fetchone()

    if session_cart:
        session_cart_id = safe_row_get(session_cart, 'id', index=0)

        if user_cart:
            user_cart_id = safe_row_get(user_cart, 'id', index=0)
            # Fusion des articles
            # MULTI-TENANT: Filtrer par tenant_id
            c.execute(adapt_query("SELECT painting_id, quantity FROM cart_items WHERE cart_id=? AND tenant_id=?"), (session_cart_id, tenant_id))
            items = c.fetchall()
            for item in items:
                painting_id = safe_row_get(item, 'painting_id', index=0)
                qty = safe_row_get(item, 'quantity', index=1)
                # MULTI-TENANT: Filtrer par tenant_id
                c.execute(adapt_query("SELECT quantity FROM cart_items WHERE cart_id=? AND painting_id=? AND tenant_id=?"),
                          (user_cart_id, painting_id, tenant_id))
                row = c.fetchone()
                if row:
                    row_qty = safe_row_get(row, 'quantity', index=0)
                    # MULTI-TENANT: Ajouter tenant_id au WHERE
                    c.execute(adapt_query("UPDATE cart_items SET quantity=? WHERE cart_id=? AND painting_id=? AND tenant_id=?"),
                              (row_qty+qty, user_cart_id, painting_id, tenant_id))
                else:
                    # MULTI-TENANT: Inclure tenant_id dans INSERT
                    c.execute(adapt_query("INSERT INTO cart_items (cart_id, painting_id, quantity, tenant_id) VALUES (?, ?, ?, ?)"),
                              (user_cart_id, painting_id, qty, tenant_id))
            # Supprime l’ancien panier de session
            c.execute(adapt_query("DELETE FROM cart_items WHERE cart_id=? AND tenant_id=?"), (session_cart_id, tenant_id))
            c.execute(adapt_query("DELETE FROM carts WHERE id=? AND tenant_id=?"), (session_cart_id, tenant_id))
        else:
            # Associe le panier de session à l'utilisateur
            c.execute(adapt_query("UPDATE carts SET user_id=? WHERE id=? AND tenant_id=?"), (user_id, session_cart_id, tenant_id))

    conn.commit()
    conn.close()

try:
    init_database(tables=TABLES)
    # Run migration to add any missing columns (e.g., tenant_id)
    # Note: migrate_db() also creates tables, but we call init_database() first
    # to ensure the connection pool is properly initialized
    migrate_db()
except Exception as e:
    print(f"[STARTUP] ⚠️  Erreur initialisation DB: {e}")
    print(f"[STARTUP] Pool size réduit pour Supabase Session mode - L'app continuera")

# NOTE: set_admin_user() moved to a route handler to avoid "Working outside of request context"
# Use the /api/admin/setup endpoint or call set_admin_user within a request context

# --------------------------------
# UTILITAIRES
# --------------------------------
def get_paintings():
    """Récupère toutes les peintures - OPTIMISÉ: colonnes spécifiques - MULTI-TENANT: filtré par tenant_id"""
    # MULTI-TENANT: Récupérer le tenant_id courant
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    # OPTIMISÉ: Sélection de colonnes spécifiques au lieu de SELECT *
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("""
        SELECT id, name, image, price, quantity, description, category, status, display_order
        FROM paintings 
        WHERE tenant_id = ?
        ORDER BY display_order DESC, id DESC
    """), (tenant_id,))
    paintings = c.fetchall()
    conn.close()
    return paintings

def is_admin():
    """Vérifie si l'utilisateur connecté est admin - MULTI-TENANT: vérifie dans le tenant courant"""
    user_id = session.get("user_id")
    if not user_id:
        return False
    
    try:
        # MULTI-TENANT: Récupérer le tenant_id courant
        tenant_id = get_current_tenant_id()
        
        conn = get_db()
        c = conn.cursor()
        # MULTI-TENANT: Vérifier que l'utilisateur appartient au tenant courant
        c.execute(adapt_query("SELECT role FROM users WHERE id=? AND tenant_id=?"), (user_id, tenant_id))
        result = c.fetchone()
        conn.close()
        
        # Vérification robuste: result doit être non vide
        if result is None:
            print(f"[is_admin] Aucun résultat pour user_id={user_id} tenant_id={tenant_id}")
            return False
        
        # Accès sécurisé au rôle avec safe_row_get
        role = safe_row_get(result, 'role', index=0)
        if role is None:
            print(f"[is_admin] Rôle NULL pour user_id={user_id} tenant_id={tenant_id}")
            return False
        
        is_admin_role = (role == 'admin')
        # Log uniquement en mode debug pour éviter le bruit et les fuites d'info
        if not is_admin_role and os.getenv('DEBUG_AUTH'):
            print(f"[is_admin] user_id={user_id} tenant_id={tenant_id} a le rôle '{role}' (non admin)")
        
        return is_admin_role
        
    except Exception as e:
        print(f"[is_admin] Erreur lors de la vérification du rôle pour user_id={user_id}: {e}")
        return False

def require_admin(f):
    """Décorateur pour protéger les routes admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash("Accès refusé. Vous devez être administrateur.")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --------------------------------
# ROUTES PUBLIQUES
# --------------------------------
@app.route('/')
def home():
    """Page d'accueil - OPTIMISÉ: requêtes spécifiques, pas de SELECT * - MULTI-TENANT: filtré par tenant_id"""
    # MULTI-TENANT: Récupérer le tenant_id courant
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()

    # OPTIMISÉ: Sélection explicite des colonnes nécessaires + LIMIT
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("""
        SELECT id, name, image, price, quantity, description, category, status
        FROM paintings 
        WHERE status = 'disponible' AND tenant_id = ?
        ORDER BY display_order DESC, id DESC 
        LIMIT 4
    """), (tenant_id,))
    latest_paintings = c.fetchall()

    # OPTIMISÉ: Sélection explicite pour toutes les peintures
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("""
        SELECT id, name, image, price, quantity, description, category, status
        FROM paintings 
        WHERE status = 'disponible' AND tenant_id = ?
        ORDER BY display_order DESC, id DESC
        LIMIT 100
    """), (tenant_id,))
    all_paintings = c.fetchall()

    conn.close()
    return render_template("index.html", latest_paintings=latest_paintings, paintings=all_paintings)

@app.route('/about')
def about():
    """Page à propos - OPTIMISÉ: colonnes spécifiques + LIMIT - MULTI-TENANT: filtré par tenant_id"""
    # MULTI-TENANT: Récupérer le tenant_id courant
    tenant_id = get_current_tenant_id()
    
    # Récupérer toutes les peintures pour affichage dans la page à propos
    conn = get_db()
    c = conn.cursor()
    # OPTIMISÉ: Colonnes spécifiques + LIMIT pour éviter de charger trop de données
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("""
        SELECT id, name, image 
        FROM paintings 
        WHERE status = 'disponible' AND tenant_id = ?
        ORDER BY display_order DESC, id DESC
        LIMIT 50
    """), (tenant_id,))
    paintings = c.fetchall()
    conn.close()

    return render_template("about.html", paintings=paintings)


@app.route('/boutique')
def boutique():
    paintings = get_paintings()
    return render_template("boutique.html", paintings=paintings)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # MULTI-TENANT: Récupérer le tenant_id courant
        tenant_id = get_current_tenant_id()
        
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = get_db()
        c = conn.cursor()
        try:
            # MULTI-TENANT: Check if email already exists within this tenant
            c.execute(adapt_query("SELECT id FROM users WHERE email=? AND tenant_id=?"), (email, tenant_id))
            existing = c.fetchone()
            if existing:
                conn.close()
                print(f"[REGISTER] Email déjà utilisé dans tenant {tenant_id}: {email}")
                flash("Cet email est déjà utilisé.")
                return redirect(url_for('register'))

            print(f"[REGISTER] Début inscription tenant {tenant_id}: {email}")
            # MULTI-TENANT: Count users within this tenant only
            c.execute(adapt_query("SELECT COUNT(*) as count FROM users WHERE tenant_id=?"), (tenant_id,))
            count_result = c.fetchone()
            user_count = safe_row_get(count_result, 'count', index=0, default=0)
            is_first_user = (user_count == 0)

            if is_first_user:
                # MULTI-TENANT: Include tenant_id in INSERT
                c.execute(adapt_query("INSERT INTO users (name, email, password, role, tenant_id) VALUES (?, ?, ?, ?, ?)"),
                          (name, email, hashed_password, 'admin', tenant_id))
                print(f"[REGISTER] Premier utilisateur {email} créé avec rôle 'admin' pour tenant {tenant_id}")
            else:
                # MULTI-TENANT: Include tenant_id in INSERT
                c.execute(adapt_query("INSERT INTO users (name, email, password, role, tenant_id) VALUES (?, ?, ?, ?, ?)"),
                          (name, email, hashed_password, 'user', tenant_id))
                print(f"[REGISTER] Utilisateur {email} créé avec rôle 'user' pour tenant {tenant_id}")

            conn.commit()
            conn.close()
            print(f"[REGISTER] Inscription réussie pour {email} (tenant {tenant_id})")
            flash("Inscription réussie !")
            return redirect(url_for('login'))
        except Exception as e:
            conn.close()
            print(f"[REGISTER] Erreur inscription: {e}")
            flash("Erreur lors de l'inscription.")
            return redirect(url_for('register'))
    return render_template("register.html")


@app.route('/api/register-preview', methods=['POST'])
def api_register_preview():
    """API endpoint pour l'inscription en preview (popup)"""
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if not name or not email or not password:
        return jsonify({"success": False, "error": "Tous les champs sont obligatoires"}), 400
    
    if len(password) < 6:
        return jsonify({"success": False, "error": "Le mot de passe doit contenir au moins 6 caractères"}), 400
    
    hashed_password = generate_password_hash(password)
    
    conn = get_db()
    c = conn.cursor()
    try:
        print(f"[REGISTER-PREVIEW] Début inscription: {email}")
        
        # check existing email first
        c.execute(adapt_query("SELECT id FROM users WHERE email=?"), (email,))
        if c.fetchone():
            conn.close()
            print(f"[REGISTER-PREVIEW ERROR] Email déjà utilisé: {email}")
            return jsonify({"success": False, "error": "Email déjà utilisé"}), 409

        c.execute(adapt_query("SELECT COUNT(*) as count FROM users"))
        count_result = c.fetchone()
        user_count = safe_row_get(count_result, 'count', index=0, default=0)
        is_first_user = (user_count == 0)
        
        if is_first_user:
            c.execute(adapt_query("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)")
                      , (name, email, hashed_password, 'admin'))
            print(f"[REGISTER-PREVIEW] Premier utilisateur {email} créé avec rôle 'admin'")
        else:
            c.execute(adapt_query("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)")
                      , (name, email, hashed_password, 'user'))
            print(f"[REGISTER-PREVIEW] Utilisateur {email} créé avec rôle 'user'")

        c.execute(adapt_query("SELECT id FROM users WHERE email=?"), (email,))
        user_result = c.fetchone()
        user_id = safe_row_get(user_result, 'id', index=0)
        
        current_domain = request.host
        c.execute(adapt_query("SELECT id FROM saas_sites WHERE sandbox_url LIKE ?"), 
                 (f"%{current_domain}%",))
        existing_site = c.fetchone()
        
        if existing_site:
            site_id = safe_row_get(existing_site, 'id', index=0)
            c.execute(adapt_query("UPDATE saas_sites SET user_id=?, status=? WHERE id=?"),
                     (user_id, 'active', site_id))
        else:
            c.execute(adapt_query("INSERT INTO saas_sites (user_id, sandbox_url, status) VALUES (?, ?, ?)"),
                     (user_id, current_domain, 'active'))
        
        conn.commit()
        conn.close()
        print(f"[REGISTER-PREVIEW] Inscription réussie pour {email}")
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "is_first_user": is_first_user,
            "show_login_modal": True
        })
    except Exception as e:
        conn.close()
        error_msg = str(e)
        print(f"[REGISTER-PREVIEW ERROR] {type(e).__name__}: {error_msg}")
        import traceback
        traceback.print_exc()
        if 'UNIQUE' in error_msg or 'unique' in error_msg:
            return jsonify({"success": False, "error": "Cet email est déjà utilisé."}), 400
        else:
            return jsonify({"success": False, "error": f"Erreur: {error_msg}"}), 500


@app.route("/api/login-preview", methods=['POST'])
def api_login_preview():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not email or not password:
        return jsonify({"success": False, "error": "Email et mot de passe requis"}), 400

    # MULTI-TENANT: Récupérer le tenant_id courant
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()

    c.execute(adapt_query("SELECT id, password FROM users WHERE email=?"), (email,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({"success": False, "error": "Email ou mot de passe incorrect"}), 401
    
    user_id = safe_row_get(user, 'id', index=0)
    user_password = safe_row_get(user, 'password', index=1)
    
    if not check_password_hash(user_password, password):
        conn.close()
        return jsonify({"success": False, "error": "Email ou mot de passe incorrect"}), 401
    
    session["user_id"] = user_id

    guest_session_id = request.cookies.get("cart_session")
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT id, session_id FROM carts WHERE user_id=? AND tenant_id=?"), (user_id, tenant_id))
    user_cart = c.fetchone()

    if user_cart:
        user_cart_session = safe_row_get(user_cart, 'session_id', index=1)
    else:
        user_cart_session = str(uuid.uuid4())
        # MULTI-TENANT: Ajouter tenant_id
        c.execute(adapt_query("INSERT INTO carts (session_id, user_id, tenant_id) VALUES (?, ?, ?)"),
                  (user_cart_session, user_id, tenant_id))
        conn.commit()

    if guest_session_id and guest_session_id != user_cart_session:
        merge_carts(user_id, guest_session_id)

    conn.close()

    resp = jsonify({"success": True})
    resp.set_cookie("cart_session", user_cart_session, max_age=60*60*24*30)
    return resp


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # MULTI-TENANT: Récupérer le tenant_id courant
        tenant_id = get_current_tenant_id()
        
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        c = conn.cursor()

        # MULTI-TENANT: Vérifier utilisateur dans ce tenant uniquement
        c.execute(adapt_query("SELECT id, password FROM users WHERE email=? AND tenant_id=?"), (email, tenant_id))
        user = c.fetchone()
        # Correction : vérifie le type et la présence des données
        if not user:
            conn.close()
            flash("Email ou mot de passe incorrect")
            return redirect(url_for("login"))
        # user peut être tuple ou dict - use safe_row_get for compatibility
        user_id = safe_row_get(user, 'id', index=0)
        user_password = safe_row_get(user, 'password', index=1)
        if not check_password_hash(user_password, password):
            conn.close()
            flash("Email ou mot de passe incorrect")
            return redirect(url_for("login"))
        session["user_id"] = user_id

        # Récupérer panier invité actuel
        guest_session_id = request.cookies.get("cart_session")

        # Vérifier si l'utilisateur a déjà un panier
        # MULTI-TENANT: Filtrer par tenant_id
        c.execute(adapt_query("SELECT id, session_id FROM carts WHERE user_id=? AND tenant_id=?"), (user_id, tenant_id))
        user_cart = c.fetchone()

        if user_cart:
            # Panier utilisateur existant → récupérer session_id
            user_cart_session = safe_row_get(user_cart, 'session_id', index=1)
        else:
            # Pas encore de panier user → en créer un
            user_cart_session = str(uuid.uuid4())
            # MULTI-TENANT: Ajouter tenant_id
            c.execute(adapt_query("INSERT INTO carts (session_id, user_id, tenant_id) VALUES (?, ?, ?)"),
                      (user_cart_session, user_id, tenant_id))
            conn.commit()

        # 🔥 Fusionner panier invité → panier utilisateur
        if guest_session_id and guest_session_id != user_cart_session:
            merge_carts(user_id, guest_session_id)

        conn.close()

        # Mettre le cookie pour utiliser le panier utilisateur
        resp = make_response(redirect(url_for("home")))
        resp.set_cookie("cart_session", user_cart_session, max_age=60*60*24*30)

        flash("Connecté avec succès !")
        return resp

    return render_template("login.html")


@app.route('/api/session-info')
def api_session_info():
    """Return basic session info for client-side checks (used by preview modals)."""
    return jsonify({
        "logged_in": bool(session.get('user_id')),
        "user_id": session.get('user_id')
    })


@app.route("/logout")
def logout():
    session.pop("user_id", None)

    # Nouveau panier invité
    guest_session = str(uuid.uuid4())

    # Le cookie utilisateur disparaît → on remet un panier invité vide
    resp = make_response(redirect(url_for("home")))
    resp.set_cookie("cart_session", guest_session, max_age=60*60*24*30)

    return resp

@app.route("/expositions")
def expositions_page():
    """Page expositions - OPTIMISÉ: colonnes spécifiques"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    # OPTIMISÉ: Sélection explicite des colonnes
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute("""
        SELECT id, title, location, date, start_time, end_time, description, image, venue_details
        FROM exhibitions 
        WHERE tenant_id=%s
        ORDER BY date ASC
        LIMIT 100
    """, (tenant_id,))
    expositions = c.fetchall()
    conn.close()

    today = date.today()

    # Cherche la prochaine exposition (la plus proche de la date d'aujourd'hui)
    next_expo = None
    other_expos = []

    for expo in expositions:
        expo_date_str = safe_row_get(expo, 'date', index=3)
        expo_date = date.fromisoformat(expo_date_str)
        if expo_date >= today and next_expo is None:
            next_expo = expo
        else:
            other_expos.append(expo)

    # Si toutes les expos sont passées, prends la dernière comme hero
    if not next_expo and expositions:
        next_expo = expositions[-1]
        other_expos = expositions[:-1]

    return render_template("expositions.html",
                           latest_expo=next_expo,
                           other_expos=other_expos)

# --------------------------------
# CRÉATIONS SUR MESURE
# --------------------------------
@app.route("/creations-sur-mesure")
def custom_orders_page():
    today = date.today().isoformat()
    return render_template("custom_orders.html", today=today)

@app.route("/creations-sur-mesure/submit", methods=["POST"])
def submit_custom_request():
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    client_name = request.form.get("client_name")
    client_email = request.form.get("client_email")
    client_phone = request.form.get("client_phone")
    project_type = request.form.get("project_type")
    description = request.form.get("description")
    dimensions = request.form.get("dimensions")
    budget = request.form.get("budget")
    deadline = request.form.get("deadline")
    
    # Gestion des images de référence
    reference_images = []
    if 'reference_images' in request.files:
        files = request.files.getlist('reference_images')
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name, ext = os.path.splitext(filename)
                unique_filename = f"custom_{timestamp}_{name}{ext}"
                
                # Créer le dossier si nécessaire
                custom_folder = os.path.join('static', 'custom_requests')
                os.makedirs(custom_folder, exist_ok=True)
                
                filepath = os.path.join(custom_folder, unique_filename)
                file.save(filepath)
                reference_images.append(f"custom_requests/{unique_filename}")
    
    # Convertir la liste en string JSON pour stockage
    import json
    reference_images_json = json.dumps(reference_images) if reference_images else None
    
    # Sauvegarder en base de données
    conn = get_db()
    c = conn.cursor()
    if IS_POSTGRES:
        # MULTI-TENANT: Inclure tenant_id dans INSERT
        c.execute(adapt_query("INSERT INTO custom_requests (client_name, client_email, client_phone, project_type, description, budget, dimensions, deadline, reference_images, status, tenant_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'En attente', ?) RETURNING id"),
                  (client_name, client_email, client_phone, project_type, description, budget, dimensions, deadline, reference_images_json, tenant_id))
        row = c.fetchone()
        request_id = safe_row_get(row, 'id', 0)
    else:
        # MULTI-TENANT: Inclure tenant_id dans INSERT
        c.execute(adapt_query("""
        INSERT INTO custom_requests (client_name, client_email, client_phone, project_type, 
                                      description, budget, dimensions, deadline, reference_images, status, tenant_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'En attente', ?)
        """), (client_name, client_email, client_phone, project_type, description, budget, dimensions, deadline, reference_images_json, tenant_id))
        request_id = c.lastrowid

    # Créer une notification pour l'admin
    # MULTI-TENANT: Inclure tenant_id dans INSERT
    c.execute(adapt_query("INSERT INTO notifications (user_id, message, type, is_read, url, tenant_id) VALUES (?, ?, ?, ?, ?, ?)") ,
              (None,  # user_id=None pour notifications admin
               f"Nouvelle demande de création sur mesure de {client_name}",
               "custom_request",
               0,
               f"/admin/custom-requests",
               tenant_id))

    conn.commit()
    conn.close()
    
    # Envoyer un email de confirmation au client
    try:
        email_sender = get_setting("email_sender") or "contact@example.com"
        smtp_password = get_setting("smtp_password")
        smtp_server = get_setting("smtp_server") or "smtp.gmail.com"
        smtp_port = int(get_setting("smtp_port") or 587)
        
        if smtp_password:
            msg = MIMEMultipart()
            msg['From'] = email_sender
            msg['To'] = client_email
            msg['Subject'] = "✨ Confirmation de votre demande de création sur mesure"
            
            # Contenu HTML de l'email
            content = f"""
            <p style="font-size: 16px; margin-bottom: 20px;">Bonjour <strong>{client_name}</strong>,</p>
            
            <p>Merci d'avoir choisi notre atelier pour créer une œuvre unique ! 🎨</p>
            
            <div style="
                background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
                border-left: 4px solid {get_setting('color_primary') or '#6366f1'};
                padding: 20px;
                margin: 25px 0;
                border-radius: 8px;
            ">
                <h3 style="margin: 0 0 15px 0; color: #1a1a1a; font-size: 18px;">📋 Récapitulatif de votre projet</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #666; font-weight: 600;">Type de projet :</td>
                        <td style="padding: 8px 0; color: #1a1a1a;">{project_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666; font-weight: 600;">Dimensions :</td>
                        <td style="padding: 8px 0; color: #1a1a1a;">{dimensions or 'À définir ensemble'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666; font-weight: 600;">Budget :</td>
                        <td style="padding: 8px 0; color: #1a1a1a;">{budget or 'À discuter'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #666; font-weight: 600;">Délai souhaité :</td>
                        <td style="padding: 8px 0; color: #1a1a1a;">{deadline or 'Flexible'}</td>
                    </tr>
                </table>
            </div>
            
            <p style="margin: 25px 0;">
                <strong>Et maintenant ?</strong><br>
                Je vais étudier votre demande avec attention et reviendrai vers vous <strong>sous 24-48h</strong> 
                pour échanger sur les détails et vous proposer un devis personnalisé.
            </p>
            
            <p style="
                background: #fff3cd;
                border: 1px solid #ffc107;
                padding: 15px;
                border-radius: 8px;
                color: #856404;
                font-size: 14px;
            ">
                💡 <strong>Conseil :</strong> Préparez vos idées, inspirations ou croquis pour notre échange. 
                Plus nous avons de détails, plus l'œuvre finale sera proche de vos attentes !
            </p>
            
            <p style="margin-top: 30px;">À très bientôt pour donner vie à votre projet ! ✨</p>
            """
            
            html_body = generate_email_html(
                title="Votre demande a bien été reçue !",
                content=content,
                button_text=None,
                button_url=None
            )
            
            msg.attach(MIMEText(html_body, 'html'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_sender, smtp_password)
            server.send_message(msg)
            server.quit()
    except Exception as e:
        print(f"Erreur envoi email: {e}")
    
    flash("Votre demande a été envoyée avec succès ! Nous vous contacterons rapidement.", "success")
    return redirect(url_for("custom_orders_page"))

# Page de détail
@app.route("/expo_detail/<int:expo_id>")
def expo_detail_page(expo_id):
    """Page détail exposition - OPTIMISÉ: colonnes spécifiques"""
    conn = get_db()
    c = conn.cursor()
    # OPTIMISÉ: Sélection explicite des colonnes + WHERE sur primary key
    c.execute(adapt_query("""
        SELECT id, title, location, date, start_time, end_time, description, image, 
               venue_details, organizer, entry_price, contact_info
        FROM exhibitions 
        WHERE id=%s
    """), (expo_id,))
    expo = c.fetchone()
    conn.close()
    if expo is None:
        return "Exposition introuvable", 404

    # Construire le chemin de l'image si elle existe
    image_url = None
    expo_image = safe_row_get(expo, 'image', index=7)
    if expo_image:  # image field
        # Vérifier si c'est déjà une URL complète
        if expo_image.startswith("http"):
            image_url = expo_image
        else:
            image_url = url_for('static', filename='expo_images/' + expo_image)

    return render_template("expo_detail.html", expo=expo, image_url=image_url)

# --------------------------------
# ROUTES ADMIN DEMANDES SUR MESURE
# --------------------------------
@app.route("/admin/custom-requests")
@require_admin
def admin_custom_requests():
    """Page admin demandes sur mesure - OPTIMISÉ: colonnes spécifiques"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    status_filter = request.args.get('status')
    
    conn = get_db()
    c = conn.cursor()
    
    # OPTIMISÉ: Sélection explicite des colonnes + filtrage avec index
    # MULTI-TENANT: Filtrer par tenant_id
    if status_filter:
        c.execute(adapt_query("""
            SELECT id, client_name, client_email, project_type, description, 
                   budget, dimensions, deadline, status, created_at
            FROM custom_requests 
            WHERE status=%s AND tenant_id=%s
            ORDER BY created_at DESC
            LIMIT 200
        """), (status_filter, tenant_id))
    else:
        c.execute("""
            SELECT id, client_name, client_email, project_type, description, 
                   budget, dimensions, deadline, status, created_at
            FROM custom_requests 
            WHERE tenant_id=%s
            ORDER BY created_at DESC
            LIMIT 200
        """, (tenant_id,))
    
    requests_list = c.fetchall()
    
    # OPTIMISÉ: Comptages avec requêtes rapides sur index
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute("SELECT COUNT(*) as count FROM custom_requests WHERE tenant_id=%s", (tenant_id,))
    result = c.fetchone()
    total_count = safe_row_get(result, 'count', index=0, default=0)
    
    c.execute("SELECT COUNT(*) as count FROM custom_requests WHERE status='En attente' AND tenant_id=%s", (tenant_id,))
    result = c.fetchone()
    pending_count = safe_row_get(result, 'count', index=0, default=0)
    
    c.execute("SELECT COUNT(*) as count FROM custom_requests WHERE status='En cours' AND tenant_id=%s", (tenant_id,))
    result = c.fetchone()
    in_progress_count = safe_row_get(result, 'count', index=0, default=0)
    
    c.execute("SELECT COUNT(*) as count FROM custom_requests WHERE status='Acceptée' AND tenant_id=%s", (tenant_id,))
    result = c.fetchone()
    accepted_count = safe_row_get(result, 'count', index=0, default=0)
    
    c.execute("SELECT COUNT(*) as count FROM custom_requests WHERE status='Refusée' AND tenant_id=%s", (tenant_id,))
    result = c.fetchone()
    refused_count = safe_row_get(result, 'count', index=0, default=0)
    
    conn.close()
    
    return render_template("admin/admin_custom_requests.html", 
                         requests=requests_list,
                         total_count=total_count,
                         pending_count=pending_count,
                         in_progress_count=in_progress_count,
                         accepted_count=accepted_count,
                         refused_count=refused_count,
                         new_notifications_count=get_new_notifications_count(),
                         active="custom_requests")

@app.route("/admin/custom-requests/<int:request_id>/status", methods=["POST"])
@require_admin
def update_custom_request_status(request_id):
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    new_status = request.form.get("status")
    
    conn = get_db()
    c = conn.cursor()
    # MULTI-TENANT: Ajouter tenant_id au WHERE
    c.execute(adapt_query("UPDATE custom_requests SET status=? WHERE id=? AND tenant_id=?"), (new_status, request_id, tenant_id))
    conn.commit()
    conn.close()
    
    flash(f"Statut mis à jour : {new_status}", "success")
    return redirect(url_for("admin_custom_requests"))

@app.route("/admin/custom-requests/<int:request_id>/delete", methods=["POST"])
@require_admin
def delete_custom_request(request_id):
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    
    # Récupérer les images avant suppression
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT reference_images FROM custom_requests WHERE id=? AND tenant_id=?"), (request_id, tenant_id))
    row = c.fetchone()
    if row:
        ref_images = safe_row_get(row, 'reference_images', index=0)
        if ref_images:
            import json
            images = json.loads(ref_images)
            for image_path in images:
                full_path = os.path.join('static', image_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
    
    # MULTI-TENANT: Ajouter tenant_id au WHERE
    c.execute(adapt_query("DELETE FROM custom_requests WHERE id=? AND tenant_id=?"), (request_id, tenant_id))
    conn.commit()
    conn.close()
    
    flash("Demande supprimée avec succès", "success")
    return redirect(url_for("admin_custom_requests"))

# --------------------------------
# ROUTES EXPOSITIONS (ADMIN)
# --------------------------------
@app.route("/admin/exhibitions")
def admin_exhibitions():
    """Page admin exhibitions - OPTIMISÉ: colonnes spécifiques"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    # OPTIMISÉ: Sélection explicite + LIMIT
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute("""
        SELECT id, title, location, date, start_time, end_time, description, image, create_date
        FROM exhibitions 
        WHERE tenant_id=%s
        ORDER BY create_date DESC
        LIMIT 200
    """, (tenant_id,))
    exhibitions = c.fetchall()
    conn.close()
    return render_template("admin/admin_exhibitions.html", 
                         exhibitions=exhibitions, 
                         new_notifications_count=get_new_notifications_count(),
                         active="exhibitions")


# Ajouter une exhibition
@app.route("/admin/exhibitions/add", methods=["GET", "POST"])
def add_exhibition():
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    # Récupérer la clé Google Places depuis les settings
    google_places_key = get_setting("google_places_key") or "CLE_PAR_DEFAUT"
    print("Google Places Key utilisée pour l'exhibition :", google_places_key)  # pour vérification

    if request.method == "POST":
        title = request.form["title"]
        location = request.form["location"]
        date = request.form["date"]
        start_time = request.form.get("start_time") or None
        end_time = request.form.get("end_time") or None
        description = request.form.get("description")
        venue_details = request.form.get("venue_details")
        organizer = request.form.get("organizer")
        entry_price = request.form.get("entry_price")
        contact_info = request.form.get("contact_info")
        file = request.files.get("image")

        image_filename = None
        if file and allowed_file(file.filename):
            # Save expo image and convert to webp; store filename only (templates prefix expo_images/)
            webp_fname = save_image_and_convert_to_webp(file, app.config['EXPO_UPLOAD_FOLDER'], db_prefix=None)
            image_filename = webp_fname

        conn = get_db()
        c = conn.cursor()
        # MULTI-TENANT: Inclure tenant_id dans INSERT
        c.execute("""
            INSERT INTO exhibitions (title, location, date, start_time, end_time, description, venue_details, organizer, entry_price, contact_info, image, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, location, date, start_time, end_time, description, venue_details, organizer, entry_price, contact_info, image_filename, tenant_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_exhibitions"))

    return render_template(
        "admin/form_exhibition.html",
        action="Ajouter",
        google_places_key=google_places_key,
        new_notifications_count=get_new_notifications_count()
    )



@app.route("/admin/exhibitions/edit/<int:exhibition_id>", methods=["GET", "POST"])
def edit_exhibition(exhibition_id):
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT * FROM exhibitions WHERE id=? AND tenant_id=?"), (exhibition_id, tenant_id))
    exhibition = c.fetchone()

    google_places_key = get_setting("google_places_key") or ""

    if request.method == "POST":
        title = request.form["title"]
        location = request.form["location"]
        date = request.form["date"]
        start_time = request.form.get("start_time") or None
        end_time = request.form.get("end_time") or None
        description = request.form.get("description")
        venue_details = request.form.get("venue_details")
        organizer = request.form.get("organizer")
        entry_price = request.form.get("entry_price")
        contact_info = request.form.get("contact_info")
        file = request.files.get("image")

        image_filename = safe_row_get(exhibition, 'image', index=5)
        if file and allowed_file(file.filename):
            webp_fname = save_image_and_convert_to_webp(file, app.config['EXPO_UPLOAD_FOLDER'], db_prefix=None)
            image_filename = webp_fname

        # MULTI-TENANT: Ajouter tenant_id au WHERE
        c.execute("""
            UPDATE exhibitions
            SET title=?, location=?, date=?, start_time=?, end_time=?, description=?, venue_details=?, organizer=?, entry_price=?, contact_info=?, image=?
            WHERE id=? AND tenant_id=?
        """, (title, location, date, start_time, end_time, description, venue_details, organizer, entry_price, contact_info, image_filename, exhibition_id, tenant_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_exhibitions"))

    conn.close()
    return render_template(
        "admin/form_exhibition.html",
        exhibition=exhibition,
        action="Éditer",
        google_places_key=google_places_key,
        new_notifications_count=get_new_notifications_count()
    )

# Supprimer une exhibition
@app.route("/admin/exhibitions/remove/<int:exhibition_id>", methods=["POST"])
def remove_exhibition(exhibition_id):
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    # Supprimer l'image du dossier si elle existe
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT image FROM exhibitions WHERE id=? AND tenant_id=?"), (exhibition_id, tenant_id))
    image = c.fetchone()
    if image:
        image_filename = safe_row_get(image, 'image', index=0)
        if image_filename:
            image_path = os.path.join(app.config['EXPO_UPLOAD_FOLDER'], image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)

    # MULTI-TENANT: Ajouter tenant_id au WHERE
    c.execute(adapt_query("DELETE FROM exhibitions WHERE id=? AND tenant_id=?"), (exhibition_id, tenant_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_exhibitions"))

# ---------------------------------------------------------
# AJOUTER UN ARTICLE AU PANIER
# ---------------------------------------------------------
@app.route('/add_to_cart/<int:painting_id>', methods=['GET', 'POST'])
def add_to_cart(painting_id):
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    cart_id, session_id = get_or_create_cart()
    conn = get_db()
    c = conn.cursor()
    
    # MULTI-TENANT: Valider que painting_id appartient au tenant courant
    c.execute(adapt_query("SELECT id FROM paintings WHERE id=? AND tenant_id=?"), (painting_id, tenant_id))
    if not c.fetchone():
        conn.close()
        flash("Peinture non trouvée", "error")
        return redirect(url_for('galerie'))
    
    # Récupérer la quantité depuis le formulaire POST ou défaut 1
    quantity_to_add = 1
    if request.method == 'POST':
        quantity_to_add = int(request.form.get('quantity', 1))

    # Vérifie si l'article existe déjà
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT quantity FROM cart_items WHERE cart_id=? AND painting_id=? AND tenant_id=?"), (cart_id, painting_id, tenant_id))
    row = c.fetchone()
    if row:
        current_qty = safe_row_get(row, 'quantity', index=0)
        new_quantity = current_qty + quantity_to_add
        # MULTI-TENANT: Ajouter tenant_id au WHERE
        c.execute(adapt_query("UPDATE cart_items SET quantity=? WHERE cart_id=? AND painting_id=? AND tenant_id=?"), (new_quantity, cart_id, painting_id, tenant_id))
    else:
        # MULTI-TENANT: Inclure tenant_id dans INSERT
        c.execute(adapt_query("INSERT INTO cart_items (cart_id, painting_id, quantity, tenant_id) VALUES (?, ?, ?, ?)"), (cart_id, painting_id, quantity_to_add, tenant_id))

    conn.commit()
    conn.close()

    resp = make_response(redirect(url_for('panier')))
    resp.set_cookie('cart_session', session_id, max_age=30*24*3600)
    return resp


# ---------------------------------------------------------
# ENLEVER 1 QUANTITÉ D’UN ARTICLE
# ---------------------------------------------------------
@app.route('/decrease_from_cart/<int:painting_id>')
def decrease_from_cart(painting_id):
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    cart_id, session_id = get_or_create_cart()
    conn = get_db()
    c = conn.cursor()

    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT quantity FROM cart_items WHERE cart_id=? AND painting_id=? AND tenant_id=?"), (cart_id, painting_id, tenant_id))
    row = c.fetchone()
    if row:
        current_qty = safe_row_get(row, 'quantity', index=0)
        new_qty = current_qty - 1
        if new_qty <= 0:
            # MULTI-TENANT: Ajouter tenant_id au WHERE
            c.execute(adapt_query("DELETE FROM cart_items WHERE cart_id=? AND painting_id=? AND tenant_id=?"), (cart_id, painting_id, tenant_id))
        else:
            # MULTI-TENANT: Ajouter tenant_id au WHERE
            c.execute(adapt_query("UPDATE cart_items SET quantity=? WHERE cart_id=? AND painting_id=? AND tenant_id=?"), (new_qty, cart_id, painting_id, tenant_id))

    conn.commit()
    conn.close()
    resp = make_response(redirect(url_for('panier')))
    resp.set_cookie('cart_session', session_id, max_age=30*24*3600)
    return resp


# ---------------------------------------------------------
# SUPPRIMER UN ARTICLE DU PANIER
# ---------------------------------------------------------
@app.route('/remove_from_cart/<int:painting_id>')
def remove_from_cart(painting_id):
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    cart_id, session_id = get_or_create_cart()
    conn = get_db()
    c = conn.cursor()

    # MULTI-TENANT: Ajouter tenant_id au WHERE
    c.execute(adapt_query("DELETE FROM cart_items WHERE cart_id=? AND painting_id=? AND tenant_id=?"), (cart_id, painting_id, tenant_id))

    conn.commit()
    conn.close()
    resp = make_response(redirect(url_for('panier')))
    resp.set_cookie('cart_session', session_id, max_age=30*24*3600)
    return resp


# ---------------------------------------------------------
# AFFICHER LE PANIER
# ---------------------------------------------------------
@app.route('/panier', endpoint='panier')
def cart():
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    cart_id, session_id = get_or_create_cart()
    conn = get_db()
    c = conn.cursor()

    # MULTI-TENANT: Filtrer cart_items et paintings par tenant_id
    c.execute(adapt_query('''
        SELECT paintings.id, paintings.name, paintings.image, paintings.price, cart_items.quantity, paintings.description
        FROM cart_items
        JOIN paintings ON cart_items.painting_id = paintings.id
        WHERE cart_items.cart_id=? AND cart_items.tenant_id=? AND paintings.tenant_id=?
    '''), (cart_id, tenant_id, tenant_id))
    items = c.fetchall()
    conn.close()

    # Calculate total using dict keys or numeric indices for compatibility
    total_price = sum(
        (item.get('price') if isinstance(item, dict) else item[3]) * 
        (item.get('quantity') if isinstance(item, dict) else item[4]) 
        for item in items
    )

    resp = make_response(render_template('cart.html', items=items, total_price=total_price))
    resp.set_cookie('cart_session', session_id, max_age=30*24*3600)
    return resp


# ---------------------------------------------------------
# INITIALISER LE COMPTEUR DE PANIER
# ---------------------------------------------------------
@app.before_request
def init_cart_count():
    if "cart_count" not in session:
        session["cart_count"] = 0


# ---------------------------------------------------------
# ROUTE CHECKOUT COMPLETE avec panier persistant
# ---------------------------------------------------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    # MULTI-TENANT: Récupérer tenant_id au début
    tenant_id = get_current_tenant_id()
    
    # Récupérer ou créer le panier
    cart_id, session_id = get_or_create_cart()

    conn = get_db()
    c = conn.cursor()

    # Récupérer les articles du panier
    # MULTI-TENANT: Filtrer cart_items et paintings par tenant_id
    c.execute(adapt_query('''
        SELECT paintings.id, paintings.name, paintings.image, paintings.price,
               cart_items.quantity AS cart_quantity, paintings.quantity AS available_qty
        FROM cart_items
        JOIN paintings ON cart_items.painting_id = paintings.id 
            AND cart_items.tenant_id = paintings.tenant_id
        WHERE cart_items.cart_id=? AND cart_items.tenant_id=? AND paintings.tenant_id=?
    '''), (cart_id, tenant_id, tenant_id))
    items = c.fetchall()

    # Normalize rows to tuples (id, name, image, price, quantity, available_qty)
    normalized_items = []
    for it in items:
        try:
            # Prefer indexed access (works for tuple-like rows)
            idv = it[0]
            namev = it[1]
            imagev = it[2]
            pricev = it[3]
            qtyv = it[4]
            availv = it[5]
        except Exception:
            # Fallback for mapping-like rows (dict, RealDictRow)
            idv = safe_row_get(it, 'id', 0)
            namev = safe_row_get(it, 'name', 1)
            imagev = safe_row_get(it, 'image', 2)
            pricev = safe_row_get(it, 'price', 3)
            # cart quantity alias is 'cart_quantity'
            qtyv = safe_row_get(it, 'cart_quantity', 4)
            # painting available quantity alias is 'available_qty'
            availv = safe_row_get(it, 'available_qty', 5)
        normalized_items.append((idv, namev, imagev, pricev, qtyv, availv))
    items = normalized_items

    # Debug: log cart contents to help diagnose missing products
    try:
        app.logger.info(f"checkout: cart_id={cart_id} items_count={len(items)} items_preview={items[:5]}")
    except Exception:
        app.logger.info(f"checkout: cart_id={cart_id} items_count=unknown (logging failed)")

    if not items:
        conn.close()
        return redirect(url_for('panier'))  # Panier vide

    total_price = sum(
        (item.get('price') if isinstance(item, dict) else item[3]) * 
        (item.get('quantity') if isinstance(item, dict) else item[4]) 
        for item in items
    )

    # Récupérer la clé Google Places depuis les settings
    google_places_key = get_setting("google_places_key") or "CLE_PAR_DEFAUT"
 
    if request.method == "POST":
        customer_name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        if not customer_name or not email or not address:
            error = "Tous les champs sont obligatoires."
            resp = make_response(render_template("checkout.html", items=items, total_price=total_price, error=error, google_places_key=google_places_key))
            resp.set_cookie('cart_session', session_id, max_age=30*24*3600)
            conn.close()
            return resp

        # Vérifier la disponibilité des stocks avant paiement
        for item in items:
            if isinstance(item, dict):
                painting_id = item.get('id')
                name = item.get('name')
                qty = item.get('quantity')
                available_qty = item.get('available_qty', item.get('quantity'))
            else:
                painting_id, name, image, price, qty, available_qty = item
            if qty > available_qty:
                error = f"Stock insuffisant pour {name} (reste {available_qty})"
                resp = make_response(render_template("checkout.html", items=items, total_price=total_price, error=error, google_places_key=google_places_key))
                resp.set_cookie('cart_session', session_id, max_age=30*24*3600)
                conn.close()
                return resp

        # Vérifier configuration Stripe
        if not stripe.api_key:
            error = "Paiement indisponible: Stripe n'est pas configuré."
            resp = make_response(render_template("checkout.html", items=items, total_price=total_price, error=error, google_places_key=google_places_key))
            resp.set_cookie('cart_session', session_id, max_age=30*24*3600)
            conn.close()
            return resp

        # Créer la session Stripe
        line_items = []
        for item in items:
            if isinstance(item, dict):
                item_name = item.get('name', 'Produit')
                item_price = item.get('price', 0)
                item_qty = item.get('quantity', 1)
            else:
                item_name = item[1]
                item_price = item[3]
                item_qty = item[4]
            
            line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': item_name},
                    'unit_amount': int(item_price * 100),
                },
                'quantity': item_qty,
            })

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.host_url + 'checkout_success',
            cancel_url=request.host_url + 'checkout'
        )

        # Sauvegarder la commande en session pour traitement après paiement
        session["pending_order"] = {
            "customer_name": customer_name,
            "email": email,
            "address": address,
            "total_price": total_price,
            "items": items
        }

        resp = make_response(redirect(checkout_session.url, code=303))
        resp.set_cookie('cart_session', session_id, max_age=30*24*3600)
        conn.close()
        return resp

    # GET : afficher le formulaire
    resp = make_response(render_template("checkout.html", items=items, total_price=total_price, google_places_key=google_places_key))
    resp.set_cookie('cart_session', session_id, max_age=30*24*3600)
    conn.close()
    return resp




@app.route("/checkout_success")
def checkout_success():
    # MULTI-TENANT: Récupérer le tenant_id courant pour filtrer toutes les requêtes
    tenant_id = get_current_tenant_id()
    
    order = session.pop("pending_order", None)
    order_id = None
    if order:
        customer_name = order["customer_name"]
        email = order["email"]
        address = order.get("address") or ""
        total_price = order["total_price"]
        items = order["items"]
        # On tente de retrouver l'order_id correspondant à cette commande
        # MULTI-TENANT: Filtrer par tenant_id pour éviter les fuites inter-tenant
        with get_db() as conn:
            c = conn.cursor()
            c.execute(adapt_query("SELECT id FROM orders WHERE email=? AND total_price=? AND tenant_id=? ORDER BY order_date DESC LIMIT 1"), (email, total_price, tenant_id))
            row = c.fetchone()
            if row:
                order_id = safe_row_get(row, 'id', 0) if isinstance(row, dict) else row[0]
    else:
        user_id = session.get("user_id")
        email = session.get("user_email")
        if not user_id and not email:
            flash("Impossible de retrouver votre commande. Veuillez contacter le support si besoin.", "error")
            return redirect(url_for('panier'))
        # MULTI-TENANT: Filtrer par tenant_id pour toutes les recherches de commandes
        with get_db() as conn:
            c = conn.cursor()
            if user_id:
                c.execute(adapt_query("SELECT * FROM orders WHERE user_id=? AND tenant_id=? ORDER BY order_date DESC LIMIT 1"), (user_id, tenant_id))
            else:
                c.execute(adapt_query("SELECT * FROM orders WHERE email=? AND tenant_id=? ORDER BY order_date DESC LIMIT 1"), (email, tenant_id))
            order_row = c.fetchone()
            if not order_row:
                flash("Aucune commande récente trouvée.", "error")
                return redirect(url_for('panier'))
            customer_name = order_row[1] if len(order_row) > 1 else ""
            email = order_row[2] if len(order_row) > 2 else ""
            address = order_row[3] if len(order_row) > 3 else ""
            total_price = order_row[4] if len(order_row) > 4 else 0
            order_id = order_row[0]
            # MULTI-TENANT: Filtrer order_items par tenant_id (sécurité supplémentaire)
            # Note: order_items a un tenant_id et une FK vers orders, donc double vérification
            c.execute(adapt_query("""
                SELECT oi.* FROM order_items oi
                INNER JOIN orders o ON oi.order_id = o.id
                WHERE oi.order_id=? AND oi.tenant_id=? AND o.tenant_id=?
            """), (order_id, tenant_id, tenant_id))
            items = c.fetchall()
    return render_template(
        "checkout_success.html",
        order_id=order_id,
        total_price=total_price
    )

@app.route("/admin/settings", methods=["GET", "POST"])
@require_admin
def admin_settings_page():
    settings_keys = [
        "stripe_secret_key",
        "google_places_key",
        "smtp_password",
        "email_sender",
        "ga4_property",
        "enable_custom_orders",
        "site_logo",
        "site_name",
        "site_slogan",
        "site_description",
        "site_about",
        "site_keywords",
        "home_title",
        "home_subtitle",
        "about_page_title",
        "about_biography_image",
        "about_biography_text",
        "about_inspiration_text",
        "about_technique_text",
        "contact_intro",
        "footer_text",
        "galerie_title",
        "galerie_description",
        "boutique_title",
        "boutique_description",
        "expositions_title",
        "expositions_description",
        "primary_color",
        "secondary_color",
        "accent_color",
        "button_text_color",
        "content_text_color",
        "button_hover_color"
    ]

    if request.method == "POST":
        # Gestion de l'upload de l'image de biographie
        image_uploaded = False
        if 'about_biography_image_file' in request.files:
            file = request.files['about_biography_image_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Générer un nom unique avec timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name, ext = os.path.splitext(filename)
                unique_filename = f"biography_{timestamp}{ext}"
                
                # Save and convert to WebP, store DB path with Images/ prefix
                db_image = save_image_and_convert_to_webp(file, app.config['UPLOAD_FOLDER'], db_prefix='Images')
                set_setting("about_biography_image", db_image)
                image_uploaded = True
        
        # Gestion de la checkbox enable_custom_orders
        enable_custom_orders = "1" if request.form.get("enable_custom_orders") else "0"
        set_setting("enable_custom_orders", enable_custom_orders)
        
        # Sauvegarder tous les autres paramètres
        for key in settings_keys:
            if key == "enable_custom_orders":
                continue  # Déjà traité ci-dessus
            elif key == "about_biography_image" and not image_uploaded:
                # Garder l'ancienne valeur si pas de nouveau fichier
                value = request.form.get(key, "")
                if value:
                    set_setting(key, value)
            elif key != "about_biography_image":
                value = request.form.get(key, "")
                set_setting(key, value)
        flash("Paramètres mis à jour avec succès !", "success")
        return redirect(url_for("admin_settings_page"))

    settings_values = {key: get_setting(key) or "" for key in settings_keys}
    # Valeurs par défaut
    defaults = {
        "site_logo": "JB Art",
        "site_name": "Jean-Baptiste Art",
        "site_slogan": "Bienvenue dans l'univers artistique de Jean-Baptiste",
        "primary_color": "#1E3A8A",
        "secondary_color": "#3B65C4",
        "accent_color": "#FF7F50",
        "button_text_color": "#FFFFFF",
        "content_text_color": "#000000",
        "button_hover_color": "#9C27B0",
        "home_title": "Découvrez mes créations",
        "about_page_title": "À propos de l'artiste",
        "about_biography_image": "Images/artiste.jpeg",
        "about_biography_text": "Présentez votre parcours artistique, vos débuts, votre évolution...",
        "about_inspiration_text": "Décrivez vos sources d'inspiration : nature, voyages, émotions...",
        "about_technique_text": "Décrivez vos techniques : acrylique, huile, techniques mixtes...",
        "galerie_title": "Galerie des œuvres",
        "galerie_description": "Découvrez la collection complète des peintures originales.",
        "boutique_title": "Boutique en ligne",
        "boutique_description": "Explorez la boutique et découvrez toutes les œuvres disponibles à la vente.",
        "expositions_title": "Expositions",
        "expositions_description": "Découvrez les expositions passées et à venir."
    }
    
    for key, default_value in defaults.items():
        if not settings_values.get(key):
            settings_values[key] = default_value

    return render_template(
        "admin/admin_settings.html",
        active="settings",
        settings=settings_values
    )


# ---------------------------------------------------------
# ROUTE AFFICHAGE DE TOUTES LES COMMANDES
# ---------------------------------------------------------
@app.route("/orders")
def orders():
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez être connecté pour voir vos commandes.")
        return redirect(url_for("login"))

    conn = get_db()
    c = conn.cursor()

    # Récupérer uniquement les commandes de l'utilisateur connecté
    c.execute("""
        SELECT id, customer_name, email, address, total_price, order_date, status
        FROM orders
        WHERE user_id=?
        ORDER BY order_date DESC
    """, (user_id,))
    orders_list = c.fetchall()

    # Récupérer les articles pour chaque commande
    all_items = {}
    for order in orders_list:
        order_id = safe_row_get(order, 'id', index=0)
        c.execute("""
            SELECT oi.painting_id, p.name, p.image, oi.price, oi.quantity
            FROM order_items oi
            JOIN paintings p ON oi.painting_id = p.id
            WHERE oi.order_id=?
        """, (order_id,))
        all_items[order_id] = c.fetchall()

    # Normaliser les articles en objets avec attributs pour les templates
    from types import SimpleNamespace
    for oid, items in list(all_items.items()):
        normalized = []
        for item in items:
            if isinstance(item, dict):
                obj = SimpleNamespace(
                    painting_id=item.get('painting_id') or item.get('id'),
                    name=item.get('name'),
                    image=item.get('image',''),
                    price=item.get('price',0),
                    quantity=item.get('quantity',0)
                )
            else:
                # tuple: painting_id, name, image, price, quantity
                obj = SimpleNamespace(
                    painting_id=item[0],
                    name=item[1],
                    image=item[2],
                    price=item[3],
                    quantity=item[4]
                )
            normalized.append(obj)
        all_items[oid] = normalized

    conn.close()

    return render_template("order.html", orders=orders_list, all_items=all_items)

@app.route('/admin/add', methods=['GET', 'POST'])
@require_admin
def add_painting_web():
    if request.method == 'POST':
        # MULTI-TENANT: Récupérer le tenant_id courant
        tenant_id = get_current_tenant_id()
        
        name = request.form['name']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])
        description = request.form.get('description', '')
        description_long = request.form.get('description_long', '')
        dimensions = request.form.get('dimensions', '')
        technique = request.form.get('technique', '')
        year = request.form.get('year', '')
        category = request.form.get('category', '')
        status = request.form.get('status', '')
        weight = request.form.get('weight', '')
        framed = 1 if request.form.get('framed') else 0
        certificate = 1 if request.form.get('certificate') else 0
        unique_piece = 1 if request.form.get('unique_piece') else 0

        if 'image' not in request.files:
            flash('Aucun fichier sélectionné')
            return redirect(request.url)
        file = request.files['image']

        if file.filename == '':
            flash('Aucun fichier sélectionné')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Save main image and convert to WebP; store DB path prefixed with Images/
            db_image = save_image_and_convert_to_webp(file, app.config['UPLOAD_FOLDER'], db_prefix='Images')
            image_path = db_image
            
            # Gestion des images additionnelles
            image_2 = None
            image_3 = None
            image_4 = None
            
            for i, field_name in enumerate(['image_2', 'image_3', 'image_4'], 2):
                if field_name in request.files:
                    file_extra = request.files[field_name]
                    if file_extra.filename and allowed_file(file_extra.filename):
                        webp_extra = save_image_and_convert_to_webp(file_extra, app.config['UPLOAD_FOLDER'], db_prefix='Images')
                        if i == 2:
                            image_2 = webp_extra
                        elif i == 3:
                            image_3 = webp_extra
                        elif i == 4:
                            image_4 = webp_extra

            create_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = get_db()
            c = conn.cursor()
            # MULTI-TENANT: Include tenant_id in INSERT
            c.execute(adapt_query("""
                INSERT INTO paintings (
                    name, image, price, quantity, description, create_date,
                    description_long, dimensions, technique, year, category, status,
                    image_2, image_3, image_4, weight, framed, certificate, unique_piece, tenant_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """), (
                name, image_path, price, quantity, description, create_date,
                description_long, dimensions, technique, year, category, status,
                image_2, image_3, image_4, weight, framed, certificate, unique_piece, tenant_id
            ))
            conn.commit()
            conn.close()

            flash('Peinture ajoutée avec succès !')
            return redirect(url_for('admin_paintings'))

        else:
            flash('Fichier non autorisé. Seules les images sont acceptées.')
            return redirect(request.url)

    return render_template('admin/add_painting.html', 
                         new_notifications_count=get_new_notifications_count())


@app.context_processor
def inject_cart():
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    session_id = request.cookies.get("cart_session")
    user_id = session.get("user_id")

    conn = get_db()
    c = conn.cursor()

    # --- PANIER ---
    cart_id = None
    if user_id:
        # MULTI-TENANT: Filtrer par tenant_id
        c.execute(adapt_query("SELECT id FROM carts WHERE user_id=? AND tenant_id=?"), (user_id, tenant_id))
        row = c.fetchone()
        if row:
            # use safe accessor to be compatible with sqlite3.Row, dicts and tuples
            cart_id = safe_row_get(row, 'id', index=0)
    elif session_id:
        # MULTI-TENANT: Filtrer par tenant_id
        c.execute(adapt_query("SELECT id FROM carts WHERE session_id=? AND tenant_id=?"), (session_id, tenant_id))
        row = c.fetchone()
        if row:
            cart_id = safe_row_get(row, 'id', index=0)

    cart_items = []
    total_qty = 0
    if cart_id:
        # MULTI-TENANT: Filtrer cart_items et paintings par tenant_id
        c.execute(adapt_query("""
            SELECT ci.painting_id, p.name, p.image, p.price, ci.quantity
            FROM cart_items ci
            JOIN paintings p ON ci.painting_id = p.id
            WHERE ci.cart_id=? AND ci.tenant_id=? AND p.tenant_id=?
        """), (cart_id, tenant_id, tenant_id))
        cart_items = c.fetchall()
        # psycopg2 returns tuples by default
        def _qty(item):
            if isinstance(item, (list, tuple)):
                return item[4]
            try:
                return item.get('quantity', 0)
            except Exception:
                try:
                    return item['quantity']
                except Exception:
                    return 0
        total_qty = sum(_qty(item) for item in cart_items)

    # --- FAVORIS ---
    favorite_ids = []
    if user_id:
        # MULTI-TENANT: Filtrer par tenant_id
        c.execute(adapt_query("SELECT painting_id FROM favorites WHERE user_id=? AND tenant_id=?"), (user_id, tenant_id))
        favorite_ids = []
        for row in c.fetchall():
            fav = safe_row_get(row, 'painting_id', index=0)
            if fav is not None:
                favorite_ids.append(fav)

    # --- NOTIFICATIONS ADMIN ---
    new_notifications_count = 0
    if is_admin():
        # MULTI-TENANT: Filtrer par tenant_id
        c.execute("SELECT COUNT(*) as count FROM notifications WHERE user_id IS NULL AND is_read=0 AND tenant_id=%s", (tenant_id,))
        result = c.fetchone()
        new_notifications_count = safe_row_get(result, 'count', index=0, default=0)

    conn.close()

    # --- PREVIEW / PRICING ---
    preview_data = None
    try:
        raw_preview = request.args.get("preview")
        if raw_preview:
            preview_data = json.loads(urllib.parse.unquote(raw_preview))
    except Exception as e:
        print(f"[SAAS] Erreur parsing preview data: {e}")

    is_preview_host = False
    preview_price = None
    try:
        is_preview_host = is_preview_request()
        if is_preview_host:
            preview_price = fetch_dashboard_site_price()
    except Exception as e:
        print(f"[SAAS] Erreur détection preview/prix: {e}")

    # --- PARAMÈTRES DU SITE ---
    site_settings = {
        "site_logo": get_setting("site_logo") or "JB Art",
        "site_name": get_setting("site_name") or "Jean-Baptiste Art",
        "site_slogan": get_setting("site_slogan") or "Bienvenue dans l'univers artistique de Jean-Baptiste",
        "site_description": get_setting("site_description") or "",
        "site_keywords": get_setting("site_keywords") or "",
        "enable_custom_orders": get_setting("enable_custom_orders") or "0",
        "home_title": get_setting("home_title") or "Découvrez mes créations",
        "home_subtitle": get_setting("home_subtitle") or "",
        "about_page_title": get_setting("about_page_title") or "À propos de l'artiste",
        "about_biography_image": get_setting("about_biography_image") or "Images/artiste.jpeg",
        "about_biography_text": get_setting("about_biography_text") or "",
        "about_inspiration_text": get_setting("about_inspiration_text") or "",
        "about_technique_text": get_setting("about_technique_text") or "",
        "contact_intro": get_setting("contact_intro") or "",
        "footer_text": get_setting("footer_text") or "",
        "galerie_title": get_setting("galerie_title") or "Galerie des œuvres",
        "galerie_description": get_setting("galerie_description") or "Découvrez la collection complète des peintures originales.",
        "boutique_title": get_setting("boutique_title") or "Boutique en ligne",
        "boutique_description": get_setting("boutique_description") or "Explorez la boutique et découvrez toutes les œuvres disponibles à la vente.",
        "expositions_title": get_setting("expositions_title") or "Expositions",
        "expositions_description": get_setting("expositions_description") or "Découvrez les expositions passées et à venir.",
        "ga4_property": get_setting("ga4_property") or "",
        "site_about": get_setting("site_about") or get_setting("about_biography_text") or "",
    }

    # Si on est en preview, on réécrit les contenus principaux pour la template de preview
    if preview_data:
        site_settings["site_logo"] = preview_data.get("logo") or preview_data.get("logo_url") or preview_data.get("logo_text") or site_settings["site_logo"]
        site_settings["site_name"] = preview_data.get("shop_name") or site_settings["site_name"]
        site_settings["site_slogan"] = preview_data.get("art_style") or site_settings["site_slogan"]
        site_settings["site_description"] = preview_data.get("bio") or site_settings["site_description"]
        site_settings["about_biography_text"] = preview_data.get("bio") or site_settings.get("about_biography_text")
        site_settings["about_inspiration_text"] = preview_data.get("art_style") or site_settings.get("about_inspiration_text")
        site_settings["about_technique_text"] = preview_data.get("art_style") or site_settings.get("about_technique_text")
        site_settings["contact_intro"] = preview_data.get("bio") or site_settings.get("contact_intro")

    return dict(
        cart_items=cart_items,
        cart_count=total_qty,
        favorite_ids=favorite_ids,
        is_admin=is_admin(),
        new_notifications_count=new_notifications_count,
        site_settings=site_settings,
        is_preview_host=is_preview_host,
        preview_price=preview_price,
        preview_data=preview_data
        ,
        stripe_publishable_key=get_setting('stripe_publishable_key')
    )


# --------------------------------
# FILTRE JINJA PERSONNALISÉ
# --------------------------------
@app.template_filter('from_json')
def from_json_filter(value):
    """Parse une chaîne JSON en objet Python"""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


@app.route("/admin/notifications")
def admin_notifications():
    if not is_admin():
        return redirect(url_for('home'))

    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()

    with get_db() as conn:
        c = conn.cursor()
        # Récupérer toutes les notifications admin (user_id=NULL)
        # MULTI-TENANT: Filtrer par tenant_id
        c.execute("""
            SELECT id, message, url, is_read, created_at 
            FROM notifications 
            WHERE user_id IS NULL AND tenant_id=%s
            ORDER BY created_at DESC
        """, (tenant_id,))
        notifications = c.fetchall()

        # Normalize notifications to tuples (id, message, url, is_read, created_at)
        normalized_notifs = []
        for n in notifications:
            if isinstance(n, dict):
                normalized_notifs.append((
                    n.get('id'),
                    n.get('message'),
                    n.get('url'),
                    n.get('is_read'),
                    n.get('created_at')
                ))
            else:
                normalized_notifs.append(n)
        notifications = normalized_notifs

        # Compter les notifications non lues
        new_notifications_count = sum(
            1 for n in notifications 
            if (n.get('is_read') if isinstance(n, dict) else n[3]) == 0
        )

    return render_template(
        "admin/admin_notifications.html",
        notifications=notifications,
        new_notifications_count=new_notifications_count,
        active="notifications"
    )

@app.route("/admin/notifications/read/<int:notif_id>")
def mark_notification_read(notif_id):
    if not is_admin():
        return redirect(url_for("home"))

    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()

    with get_db() as conn:
        c = conn.cursor()
        # Mettre la notification comme lue
        # MULTI-TENANT: Ajouter tenant_id au WHERE
        c.execute(adapt_query("UPDATE notifications SET is_read=1 WHERE id=? AND tenant_id=?"), (notif_id, tenant_id))
        # Récupérer l'URL pour redirection
        # MULTI-TENANT: Filtrer par tenant_id
        c.execute(adapt_query("SELECT url FROM notifications WHERE id=? AND tenant_id=?"), (notif_id, tenant_id))
        row = c.fetchone()
        redirect_url = safe_row_get(row, 'url', index=0) or url_for("admin_notifications")

    return redirect(redirect_url)


# --------------------------------
# ROUTE GALERIE
# --------------------------------
@app.route('/galerie')
def galerie():
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute("SELECT id, name, image, price, quantity FROM paintings WHERE tenant_id=%s ORDER BY display_order ASC, id DESC", (tenant_id,))
    paintings = c.fetchall()
    conn.close()
    
    # Vérifier si l'utilisateur est admin
    user_is_admin = is_admin()
    
    return render_template('galerie.html', paintings=paintings, user_is_admin=user_is_admin)

@app.route('/api/reorder_paintings', methods=['POST'])
def reorder_paintings():
    """Route API pour réorganiser l'ordre des peintures (admin seulement)"""
    if not is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    data = request.get_json()
    painting_ids = data.get('order', [])
    
    if not painting_ids:
        return jsonify({'error': 'No order provided'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # Mettre à jour l'ordre d'affichage
    # MULTI-TENANT: Ajouter tenant_id au WHERE
    for index, painting_id in enumerate(painting_ids):
        c.execute(adapt_query(
            "UPDATE paintings SET display_order = ? WHERE id = ? AND tenant_id = ?"
        ), (index, painting_id, tenant_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Ordre mis à jour'})

# --------------------------------
# ROUTE PAGE PRODUIT DÉTAILLÉE
# --------------------------------

@app.route('/painting/<int:painting_id>')
def painting_detail(painting_id):
    conn = get_db()
    c = conn.cursor()
    
    # Récupérer les détails complets de la peinture
    query = adapt_query("""
        SELECT id, name, image, price, quantity, description, description_long,
               dimensions, technique, year, category, status, image_2, image_3, image_4,
               weight, framed, certificate, unique_piece
        FROM paintings WHERE id = ?
    """)
    c.execute(query, (painting_id,))
    painting = c.fetchone()
    
    if not painting:
        conn.close()
        abort(404)
    
    # Convertir en dict pour faciliter l'accès si ce n'est pas déjà un dict
    if isinstance(painting, dict):
        painting_dict = painting
    else:
        painting_dict = {
            'id': painting[0],
            'name': painting[1],
            'image': painting[2],
            'price': painting[3],
            'quantity': painting[4],
            'description': painting[5],
            'description_long': painting[6],
            'dimensions': painting[7],
            'technique': painting[8],
            'year': painting[9],
            'category': painting[10],
            'status': painting[11],
            'image_2': painting[12],
            'image_3': painting[13],
            'image_4': painting[14],
            'weight': painting[15],
            'framed': painting[16],
            'certificate': painting[17],
            'unique_piece': painting[18]
        }
    
    # Récupérer des peintures similaires (même catégorie ou aléatoire)
    if painting_dict['category']:
        query_similar = adapt_query("""
            SELECT id, name, image, price 
            FROM paintings 
            WHERE category = ? AND id != ? AND quantity > 0
            LIMIT 4
        """)
        c.execute(query_similar, (painting_dict['category'], painting_id))
    else:
        query_similar = adapt_query("""
            SELECT id, name, image, price 
            FROM paintings 
            WHERE id != ? AND quantity > 0
            ORDER BY RANDOM()
            LIMIT 4
        """)
        c.execute(query_similar, (painting_id,))
    
    similar_paintings = c.fetchall()
    conn.close()
    
    return render_template('painting_detail.html', painting=painting_dict, similar_paintings=similar_paintings)

# --------------------------------
# ROUTE CONTACT
# --------------------------------

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name').strip()
        email = request.form.get('email').strip()
        message = request.form.get('message').strip()

        if not name or not email or not message:
            flash("Tous les champs sont obligatoires.")
            return redirect(url_for('contact'))

        # Configuration email
        SMTP_SERVER = get_setting("smtp_server") or "smtp.gmail.com"
        SMTP_PORT = int(get_setting("smtp_port") or 587)
        SMTP_USER = get_setting("email_sender") or "coco.cayre@gmail.com"
        SMTP_PASSWORD = get_setting("smtp_password") or "motdepassepardefaut"

        try:
            msg = MIMEMultipart()
            msg['From'] = SMTP_USER
            msg['To'] = SMTP_USER  # Envoie à toi-même
            msg['Subject'] = f"Message depuis le formulaire de contact - {name}"

            # Corps du mail en HTML stylé comme le site
            body = f"""
            <html>
            <body style="font-family: 'Poppins', sans-serif; background:#f0f4f8; padding:20px;">
                <div style="max-width:600px; margin:auto; background:white; border-radius:15px; overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.1);">
                    <h2 style="color:#1E3A8A; text-align:center;">Nouveau message depuis le formulaire de contact</h2>
                    <hr style="border:none; border-top:2px solid #1E3A8A; margin:20px 0;">
                    <p><strong>Nom :</strong> {name}</p>
                    <p><strong>Email :</strong> {email}</p>
                    <p><strong>Message :</strong></p>
                    <div style="padding:15px; background:#f9f9f9; border-radius:8px; line-height:1.5; color:#333;">
                        {message}
                    </div>
                    <hr style="border:none; border-top:2px solid #1E3A8A; margin:20px 0;">
                    <p style="text-align:center; color:#555;">JB Art - Formulaire de contact</p>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()

            flash("Votre message a été envoyé avec succès !")
        except Exception as e:
            print(e)
            flash("Une erreur est survenue, veuillez réessayer plus tard.")

        return redirect(url_for('contact'))

    return render_template('contact.html')


@app.route('/profile')
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez être connecté pour accéder à votre profil.")
        return redirect(url_for("login"))

    conn = get_db()
    c = conn.cursor()

    # Récupérer les infos de l'utilisateur connecté
    c.execute(adapt_query("SELECT id, name, email, create_date FROM users WHERE id=?"), (user_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        flash("Utilisateur introuvable.")
        return redirect(url_for("home"))

    # Récupérer uniquement les commandes de l'utilisateur connecté
    c.execute("""
        SELECT id, customer_name, email, address, total_price, order_date, status
        FROM orders
        WHERE user_id=?
        ORDER BY order_date DESC
    """, (user_id,))
    user_orders = c.fetchall()

    # Récupérer les articles pour chaque commande
    all_items = {}
    order_totals = {}
    for order in user_orders:
        order_id = safe_row_get(order, 'id', index=0)
        c.execute("""
            SELECT oi.painting_id, p.name, p.image, oi.price, oi.quantity
            FROM order_items oi
            JOIN paintings p ON oi.painting_id = p.id
            WHERE oi.order_id=?
        """, (order_id,))
        items = c.fetchall()
        all_items[order_id] = items
        order_totals[order_id] = sum(
            (item.get('price') if isinstance(item, dict) else item[3]) * 
            (item.get('quantity') if isinstance(item, dict) else item[4]) 
            for item in items
        )

    # Récupérer les peintures favorites de l'utilisateur (hors boucle)
    favorite_paintings = []
    c.execute("""
        SELECT p.id, p.name, p.image, p.price, p.quantity, p.description
        FROM paintings p
        JOIN favorites f ON p.id = f.painting_id
        WHERE f.user_id=?
        ORDER BY f.created_date DESC
        LIMIT 6
    """, (user_id,))
    favorite_paintings = c.fetchall()

    # Formater les commandes pour le template
    formatted_orders = []
    for order in user_orders:
        if isinstance(order, dict):
            formatted_orders.append({
                'id': order.get('id'),
                'customer_name': order.get('customer_name'),
                'email': order.get('email'),
                'address': order.get('address'),
                'total': order.get('total_price'),
                'date': order.get('order_date'),
                'status': order.get('status')
            })
        else:
            formatted_orders.append({
                'id': order[0],
                'customer_name': order[1],
                'email': order[2],
                'address': order[3],
                'total': order[4],
                'date': order[5],
                'status': order[6]
            })

    conn.close()

    # Format user data
    if isinstance(user, dict):
        user_data = {
            'id': user.get('id'),
            'name': user.get('name'),
            'email': user.get('email'),
            'create_date': user.get('create_date')
        }
    else:
        user_data = {
            'id': user[0],
            'name': user[1],
            'email': user[2],
            'create_date': user[3]
        }

    return render_template(
        "profile.html",
        user=user_data,
        orders=formatted_orders,
        all_items=all_items,
        order_totals=order_totals,
        orders_count=len(user_orders),
        favorite_paintings=favorite_paintings
    )


# --------------------------------
# ROUTE DOWNLOAD INVOICE PDF (compatible Windows)
# --------------------------------
@app.route('/download_invoice/<int:order_id>')
def download_invoice(order_id):
    order = get_order_by_id(order_id)
    items = get_order_items(order_id)
    if not order:
        return "Commande introuvable.", 404

    total_price = sum(
        (item.get('price') if isinstance(item, dict) else item[3]) * 
        (item.get('quantity') if isinstance(item, dict) else item[4]) 
        for item in items
    )

    # PDF en mémoire
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    # --- Couleurs ---
    primary_color = colors.HexColor("#1E3A8A")
    grey_color = colors.HexColor("#333333")
    light_grey = colors.HexColor("#F5F5F5")

    # Extract order fields safely
    if isinstance(order, dict):
        order_id = order.get('id')
        customer_name = order.get('customer_name')
        email = order.get('email')
        address = order.get('address')
        order_date = order.get('order_date')
        status = order.get('status')
    else:
        order_id = order[0]
        customer_name = order[1]
        email = order[2]
        address = order[3]
        order_date = order[5]
        status = order[6]

    # --- En-tête ---
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(50, height - 50, "JB Art")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 80, f"Facture - Commande #{order_id}")

    c.setLineWidth(2)
    c.line(50, height - 95, width - 50, height - 95)

    # --- Infos client ---
    c.setFont("Helvetica", 12)
    c.setFillColor(grey_color)
    c.drawString(50, height - 120, f"Nom: {customer_name}")
    c.drawString(50, height - 140, f"Email: {email}")
    c.drawString(50, height - 160, f"Adresse: {address}")
    c.drawString(50, height - 180, f"Date: {order_date}")
    c.drawString(50, height - 200, f"Statut: {status}")

    # --- Tableau des articles ---
    y = height - 230
    c.drawString(50, y, "Articles:")
    y -= 20
    for item in items:
        if isinstance(item, dict):
            item_name = item.get('name')
            item_quantity = item.get('quantity')
            item_price = item.get('price')
        else:
            item_name = item[1]
            item_quantity = item[4]
            item_price = item[3]
        c.drawString(60, y, f"{item_name} x {item_quantity} - {item_price} €")
        y -= 20

    # Total
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y-20, f"Total: {total_price} €")

    c.save()
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"facture_{order_id}.pdf",
        mimetype='application/pdf'
    )

# ---------------------------------------------------------
# ROUTES FAVORIS
# ---------------------------------------------------------
@app.route('/add_favorite/<int:painting_id>')
def add_favorite(painting_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez être connecté pour ajouter aux favoris.")
        return redirect(url_for("login"))

    # MULTI-TENANT: Récupérer le tenant_id courant
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()

    try:
        # MULTI-TENANT: Vérifier que la peinture appartient au même tenant
        c.execute(adapt_query("SELECT id FROM paintings WHERE id=? AND tenant_id=?"), (painting_id, tenant_id))
        painting = c.fetchone()
        if not painting:
            conn.close()
            flash("Peinture non trouvée.")
            return redirect(url_for('home'))
        
        # MULTI-TENANT: Vérifier que l'utilisateur appartient au même tenant
        c.execute(adapt_query("SELECT id FROM users WHERE id=? AND tenant_id=?"), (user_id, tenant_id))
        user = c.fetchone()
        if not user:
            conn.close()
            flash("Erreur d'authentification.")
            return redirect(url_for('login'))
        
        # MULTI-TENANT: Insert avec tenant_id
        c.execute(adapt_query("INSERT INTO favorites (user_id, painting_id, tenant_id) VALUES (?, ?, ?)"), 
                  (user_id, painting_id, tenant_id))
        conn.commit()
        flash("Ajouté aux favoris !")
    except Exception as e:
        # IntegrityError pour doublon (favoris déjà existant)
        if 'UNIQUE' in str(e) or 'unique' in str(e) or 'duplicate' in str(e).lower():
            flash("Cette peinture est déjà dans vos favoris.")
        else:
            print(f"[FAVORITES] Erreur ajout favori: {e}")
            flash("Erreur lors de l'ajout aux favoris.")
    finally:
        conn.close()

    return redirect(request.referrer or url_for('home'))

@app.route('/remove_favorite/<int:painting_id>')
def remove_favorite(painting_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez être connecté.")
        return redirect(url_for("login"))

    # MULTI-TENANT: Récupérer le tenant_id courant
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()

    # MULTI-TENANT: Delete avec tenant_id pour isolation stricte
    c.execute(adapt_query("DELETE FROM favorites WHERE user_id=? AND painting_id=? AND tenant_id=?"), 
              (user_id, painting_id, tenant_id))
    conn.commit()
    conn.close()

    flash("Retiré des favoris !")
    return redirect(request.referrer or url_for('home'))

@app.route('/is_favorite/<int:painting_id>')
def is_favorite(painting_id):
    user_id = session.get("user_id")
    if not user_id:
        return {'is_favorite': False}

    # MULTI-TENANT: Récupérer le tenant_id courant
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()

    # MULTI-TENANT: Check avec tenant_id
    c.execute(adapt_query("SELECT 1 FROM favorites WHERE user_id=? AND painting_id=? AND tenant_id=?"), 
              (user_id, painting_id, tenant_id))
    result = c.fetchone()
    conn.close()

    return {'is_favorite': result is not None}

# --------------------------------
# ROUTES ADMINISTRATION
# --------------------------------
@app.route('/admin')
@require_admin
def admin_dashboard():
    """Tableau de bord administrateur - MULTI-TENANT: filtré par tenant_id"""
    # MULTI-TENANT: Récupérer le tenant_id courant
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    
    # MULTI-TENANT: Statistiques filtrées par tenant_id
    c.execute(adapt_query("SELECT COUNT(*) as count FROM paintings WHERE tenant_id=?"), (tenant_id,))
    result = c.fetchone()
    total_paintings = safe_row_get(result, 'count', index=0, default=0)
    
    c.execute(adapt_query("SELECT COUNT(*) as count FROM orders WHERE tenant_id=?"), (tenant_id,))
    result = c.fetchone()
    total_orders = safe_row_get(result, 'count', index=0, default=0)
    
    c.execute(adapt_query("SELECT SUM(total_price) as total FROM orders WHERE tenant_id=?"), (tenant_id,))
    result = c.fetchone()
    total_revenue = safe_row_get(result, 'total', index=0, default=0) or 0
    
    c.execute(adapt_query("SELECT COUNT(*) as count FROM users WHERE tenant_id=?"), (tenant_id,))
    result = c.fetchone()
    total_users = safe_row_get(result, 'count', index=0, default=0)
    
    # MULTI-TENANT: Dernières commandes de ce tenant uniquement
    c.execute(adapt_query("""
        SELECT id, customer_name, email, total_price, order_date, status 
        FROM orders 
        WHERE tenant_id=?
        ORDER BY order_date DESC 
        LIMIT 5
    """), (tenant_id,))
    recent_orders = c.fetchall()
    # Normalize recent_orders to tuples (id, customer_name, email, total_price, order_date, status)
    normalized_recent = []
    for r in recent_orders:
        if isinstance(r, dict):
            normalized_recent.append((
                r.get('id'),
                r.get('customer_name'),
                r.get('email'),
                r.get('total_price'),
                r.get('order_date'),
                r.get('status')
            ))
        else:
            normalized_recent.append(r)
    recent_orders = normalized_recent
    
    # Peintures en rupture de stock
    c.execute("""
        SELECT id, name, price, quantity 
        FROM paintings 
        WHERE quantity <= 0 
        ORDER BY id DESC
    """)
    out_of_stock = c.fetchall()
    # Normalize out_of_stock to tuples (id, name, price, quantity)
    normalized_oos = []
    for p in out_of_stock:
        if isinstance(p, dict):
            normalized_oos.append((
                p.get('id'),
                p.get('name'),
                p.get('price'),
                p.get('quantity')
            ))
        else:
            normalized_oos.append(p)
    out_of_stock = normalized_oos
    
    # Produits les plus vendus (TOP 5)
    c.execute(adapt_query("""
        SELECT p.id, p.name, p.image, p.price, SUM(oi.quantity) as total_sold
        FROM paintings p
        JOIN order_items oi ON p.id = oi.painting_id
        GROUP BY p.id, p.name, p.image, p.price
        ORDER BY total_sold DESC
        LIMIT 5
    """))
    top_selling = c.fetchall()
    # Normalize top_selling to tuples (id, name, image, price, total_sold)
    normalized_top = []
    for p in top_selling:
        if isinstance(p, dict):
            normalized_top.append((
                p.get('id'),
                p.get('name'),
                p.get('image'),
                p.get('price'),
                p.get('total_sold')
            ))
        else:
            normalized_top.append(p)
    top_selling = normalized_top
    
    # Produits les plus aimés (TOP 5)
    c.execute(adapt_query("""
        SELECT p.id, p.name, p.image, p.price, COUNT(f.id) as favorite_count
        FROM paintings p
        JOIN favorites f ON p.id = f.painting_id
        GROUP BY p.id, p.name, p.image, p.price
        ORDER BY favorite_count DESC
        LIMIT 5
    """))
    most_loved = c.fetchall()
    # Normalize most_loved to tuples (id, name, image, price, favorite_count)
    normalized_loved = []
    for p in most_loved:
        if isinstance(p, dict):
            normalized_loved.append((
                p.get('id'),
                p.get('name'),
                p.get('image'),
                p.get('price'),
                p.get('favorite_count')
            ))
        else:
            normalized_loved.append(p)
    most_loved = normalized_loved
    
    # Compter les notifications non lues
    c.execute("""
        SELECT COUNT(*) as count
        FROM notifications 
        WHERE user_id IS NULL AND is_read = 0
    """)
    result = c.fetchone()
    new_notifications_count = safe_row_get(result, 'count', index=0, default=0)
    
    conn.close()
    
    return render_template('admin/admin_dashboard.html',
                         total_paintings=total_paintings,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         total_users=total_users,
                         recent_orders=recent_orders,
                         out_of_stock=out_of_stock,
                         top_selling=top_selling,
                         most_loved=most_loved,
                         new_notifications_count=new_notifications_count,
                         active="dashboard")


# Route désactivée - L'API est gérée automatiquement
# @app.route('/admin/api-export')
# @require_admin
# def admin_api_export():
#     """Page de gestion de l'API d'export"""
#     api_key = get_setting("export_api_key")
#     if not api_key:
#         api_key = secrets.token_urlsafe(32)
#         set_setting("export_api_key", api_key)
#     
#     return render_template('admin/api_export.html', api_key=api_key, active="api")


@app.route('/admin/paintings')
@require_admin
def admin_paintings():
    """Gestion des peintures"""
    paintings = get_paintings()
    return render_template('admin/admin_paintings.html', 
                         paintings=paintings, 
                         new_notifications_count=get_new_notifications_count(),
                         active="paintings")

@app.route('/admin/painting/remove/<int:painting_id>', methods=['POST'])
def remove_painting(painting_id):
    if not is_admin():
        return redirect(url_for('home'))

    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()

    with get_db() as conn:
        c = conn.cursor()
        # MULTI-TENANT: Ajouter tenant_id au WHERE
        c.execute(adapt_query("DELETE FROM paintings WHERE id=? AND tenant_id=?"), (painting_id, tenant_id))
        conn.commit()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/painting/edit/<int:painting_id>', methods=['GET', 'POST'])
@require_admin
def edit_painting(painting_id):
    """Éditer une peinture"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    
    # Récupérer la peinture avec tous les champs
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("""
        SELECT id, name, image, price, quantity, description, create_date,
               description_long, dimensions, technique, year, category, status,
               image_2, image_3, image_4, weight, framed, certificate, unique_piece
        FROM paintings WHERE id=? AND tenant_id=?
    """), (painting_id, tenant_id))
    painting = c.fetchone()
    
    if not painting:
        conn.close()
        flash("Peinture introuvable.")
        return redirect(url_for('admin_paintings'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = request.form.get('price', '0').strip()
        quantity = request.form.get('quantity', '0').strip()
        description = request.form.get('description', '').strip()
        description_long = request.form.get('description_long', '').strip()
        dimensions = request.form.get('dimensions', '').strip()
        technique = request.form.get('technique', '').strip()
        year = request.form.get('year', '').strip()
        category = request.form.get('category', '').strip()
        status = request.form.get('status', '').strip()
        weight = request.form.get('weight', '').strip()
        framed = 1 if request.form.get('framed') else 0
        certificate = 1 if request.form.get('certificate') else 0
        unique_piece = 1 if request.form.get('unique_piece') else 0
        
        if not name or price == '' or quantity == '':
            flash("Tous les champs sont obligatoires.")
            conn.close()
            return redirect(url_for('edit_painting', painting_id=painting_id))
        
        try:
            price = float(price)
            quantity = int(quantity)

            # Gestion des images (principale + 3 additionnelles)
            if isinstance(painting, dict):
                image_fields = {
                    'image': painting.get('image'),
                    'image_2': painting.get('image_2'),
                    'image_3': painting.get('image_3'),
                    'image_4': painting.get('image_4')
                }
            else:
                image_fields = {
                    'image': painting[2],
                    'image_2': painting[13],
                    'image_3': painting[14],
                    'image_4': painting[15]
                }
            
            for field_name, current_value in image_fields.items():
                file = request.files.get(field_name)
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(save_path)
                    
                    # Supprimer l'ancienne image
                    try:
                        if current_value:
                            old_path = current_value if current_value.startswith("static") else os.path.join('static', current_value)
                            if os.path.exists(old_path) and os.path.abspath(old_path) != os.path.abspath(save_path):
                                os.remove(old_path)
                    except Exception:
                        pass
                    
                    image_fields[field_name] = f"Images/{filename}"

            # Update BDD avec tous les champs
            # MULTI-TENANT: Ajouter tenant_id au WHERE
            c.execute(adapt_query("""
                UPDATE paintings SET 
                    name=?, price=?, quantity=?, image=?, description=?,
                    description_long=?, dimensions=?, technique=?, year=?, 
                    category=?, status=?, image_2=?, image_3=?, image_4=?,
                    weight=?, framed=?, certificate=?, unique_piece=?
                WHERE id=? AND tenant_id=?
            """), (
                name, price, quantity, image_fields['image'], description,
                description_long, dimensions, technique, year,
                category, status, image_fields['image_2'], image_fields['image_3'], image_fields['image_4'],
                weight, framed, certificate, unique_piece,
                painting_id, tenant_id
            ))
            conn.commit()
            flash("Peinture mise à jour avec succès !")
            conn.close()
            return redirect(url_for('admin_paintings'))
        
        except ValueError:
            flash("Prix et quantité doivent être des nombres.")
            conn.close()
            return redirect(url_for('edit_painting', painting_id=painting_id))
    
    conn.close()
    return render_template('admin/edit_painting.html', 
                         painting=painting, 
                         new_notifications_count=get_new_notifications_count())

@app.route('/admin/painting/delete/<int:painting_id>')
@require_admin
def delete_painting(painting_id):
    """Supprimer une peinture"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()
    
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT image FROM paintings WHERE id=? AND tenant_id=?"), (painting_id, tenant_id))
    painting = c.fetchone()
    
    if painting:
        # Supprimer le fichier image
        image_filename = painting.get('image') if isinstance(painting, dict) else painting[0]
        if image_filename:
            image_path = os.path.join('static', image_filename)
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except:
                    pass
        
        # Supprimer de la BD
        # MULTI-TENANT: Ajouter tenant_id au WHERE
        c.execute(adapt_query("DELETE FROM paintings WHERE id=? AND tenant_id=?"), (painting_id, tenant_id))
        conn.commit()
        flash("Peinture supprimée avec succès !")
    else:
        flash("Peinture introuvable.")
    
    conn.close()
    return redirect(url_for('admin_paintings'))

@app.route('/admin/orders')
@require_admin
def admin_orders():
    """Gestion des commandes avec recherche et filtre par rôle"""
    q = request.args.get('q', '').strip().lower()  # récupération du terme de recherche
    conn = get_db()
    c = conn.cursor()

    if q:
        # Requête avec recherche par ID ou nom client
        c.execute(adapt_query("""
            SELECT o.id, o.customer_name, o.email, o.address, o.total_price, o.order_date, o.status
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN paintings p ON oi.painting_id = p.id
            WHERE o.id LIKE ? 
               OR LOWER(o.customer_name) LIKE ?
               OR LOWER(o.email) LIKE ?
               OR LOWER(p.name) LIKE ?
            GROUP BY o.id
            ORDER BY o.order_date DESC
        """), (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"))
    else:
        # Si pas de recherche, tout afficher
        c.execute("""
            SELECT id, customer_name, email, address, total_price, order_date, status 
            FROM orders 
            ORDER BY order_date DESC
        """)

    orders_list = c.fetchall()

    # Récupérer les articles pour chaque commande
    all_items = {}
    for order in orders_list:
        order_id = safe_row_get(order, 'id', index=0)
        c.execute(adapt_query("""
            SELECT oi.painting_id, p.name, p.image, oi.price, oi.quantity
            FROM order_items oi
            JOIN paintings p ON oi.painting_id = p.id
            WHERE oi.order_id=?
        """), (order_id,))
        all_items[order_id] = c.fetchall()

    # Normaliser les commandes en objets avec attributs pour les templates (order.total_price, etc.)
    from types import SimpleNamespace
    orders_objs = []
    for order in orders_list:
        if isinstance(order, dict):
            o = SimpleNamespace(
                id=order.get('id'),
                customer_name=order.get('customer_name'),
                email=order.get('email'),
                address=order.get('address'),
                total_price=order.get('total_price'),
                order_date=order.get('order_date'),
                status=order.get('status')
            )
        else:
            o = SimpleNamespace(
                id=order[0],
                customer_name=order[1],
                email=order[2],
                address=order[3],
                total_price=order[4],
                order_date=order[5],
                status=order[6]
            )
        orders_objs.append(o)

    # Normaliser les articles en objets avec attributs pour les templates
    from types import SimpleNamespace
    for oid, items in list(all_items.items()):
        normalized = []
        for item in items:
            if isinstance(item, dict):
                obj = SimpleNamespace(
                    painting_id=item.get('painting_id') or item.get('id'),
                    name=item.get('name'),
                    image=item.get('image',''),
                    price=item.get('price',0),
                    quantity=item.get('quantity',0)
                )
            else:
                obj = SimpleNamespace(
                    painting_id=item[0],
                    name=item[1],
                    image=item[2],
                    price=item[3],
                    quantity=item[4]
                )
            normalized.append(obj)
        all_items[oid] = normalized

    conn.close()
    return render_template('admin/admin_orders.html', 
                         orders=orders_objs, 
                         all_items=all_items, 
                         new_notifications_count=get_new_notifications_count(),
                         active="orders")

@app.route("/order/<int:order_id>")
def order_status(order_id):
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    conn = get_db()
    c = conn.cursor()

    # Récupérer la commande
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT id, customer_name, email, address, total_price, order_date, status FROM orders WHERE id=? AND tenant_id=?"), (order_id, tenant_id))
    order = c.fetchone()
    if not order:
        conn.close()
        abort(404)

    # Récupérer les articles avec info peinture
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute("""
        SELECT oi.painting_id, p.name, p.image, oi.price, oi.quantity
        FROM order_items oi
        JOIN paintings p ON oi.painting_id = p.id
        WHERE oi.order_id=? AND oi.tenant_id=?
    """, (order_id, tenant_id))
    items = c.fetchall()

    conn.close()

    total_price = safe_row_get(order, 'total_price', index=4)

    return render_template(
        "order_status.html",
        order=order,
        items=items,
        total_price=total_price
    )


@app.route('/admin/order/<int:order_id>/status/<status>')
@require_admin
def update_order_status(order_id, status):
    """Mettre à jour le statut d'une commande"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    valid_statuses = ['En cours', 'Confirmée', 'Expédiée', 'Livrée', 'Annulée']
    
    if status not in valid_statuses:
        flash("Statut invalide.")
        return redirect(url_for('admin_orders'))
    
    conn = get_db()
    c = conn.cursor()
    
    # MULTI-TENANT: Ajouter tenant_id au WHERE
    c.execute(adapt_query("UPDATE orders SET status=? WHERE id=? AND tenant_id=?"), (status, order_id, tenant_id))
    conn.commit()
    conn.close()
    
    flash(f"Commande #{order_id} mise à jour : {status}")
    return redirect(url_for('admin_orders'))


@app.route("/admin/orders/<int:order_id>")
def admin_order_detail(order_id):
    """Détail commande - OPTIMISÉ: colonnes spécifiques + JOIN au lieu de N+1"""
    if not is_admin():
        return redirect(url_for("home"))

    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()

    conn = get_db()
    c = conn.cursor()

    # OPTIMISÉ: Récupérer la commande avec colonnes spécifiques
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("""
        SELECT id, customer_name, email, address, total_price, order_date, status 
        FROM orders 
        WHERE id=%s AND tenant_id=%s
    """), (order_id, tenant_id))
    order = c.fetchone()
    if not order:
        conn.close()
        return "Commande introuvable", 404

    # OPTIMISÉ: JOIN au lieu de requête séparée (évite N+1)
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute("""
        SELECT oi.painting_id, p.name, p.image, oi.price, oi.quantity
        FROM order_items oi
        JOIN paintings p ON oi.painting_id = p.id
        WHERE oi.order_id=%s AND oi.tenant_id=%s
    """, (order_id, tenant_id))
    items = c.fetchall()
    # Ensure items are tuples (template expects numeric indexes)
    normalized_items = []
    for r in items:
        if hasattr(r, 'get'):
            # r is mapping-like
            normalized_items.append((r.get('painting_id'), r.get('name'), r.get('image'), r.get('price'), r.get('quantity')))
        else:
            normalized_items.append(tuple(r))
    items = normalized_items
    conn.close()

    # Normalize order to tuple for templates that use numeric indexes
    if hasattr(order, 'get'):
        order = (
            order.get('id'),
            order.get('customer_name'),
            order.get('email'),
            order.get('address'),
            order.get('total_price'),
            order.get('order_date'),
            order.get('status')
        )

    return render_template("admin/admin_order_detail.html", 
                         order=order, 
                         items=items, 
                         new_notifications_count=get_new_notifications_count())


@app.route('/admin/users')
@require_admin
def admin_users():
    """Gestion des utilisateurs avec recherche et filtre par rôle - OPTIMISÉ"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    q = request.args.get('q', '').strip().lower()
    role = request.args.get('role', '').strip().lower()
    
    conn = get_db()
    c = conn.cursor()

    # OPTIMISÉ: Sélection explicite des colonnes + LIMIT
    # MULTI-TENANT: Filtrer par tenant_id
    query = """
        SELECT id, name, email, role, create_date 
        FROM users
        WHERE tenant_id=%s
    """
    conditions = []
    params = [tenant_id]

    # Recherche texte
    if q:
        conditions.append("""(
            CAST(id AS TEXT) LIKE %s
            OR LOWER(name) LIKE %s
            OR LOWER(email) LIKE %s
            OR LOWER(role) LIKE %s
            OR LOWER(create_date) LIKE %s
        )""")
        params.extend([f"%{q}%" ] * 5)

    # Filtre rôle - utilise l'index idx_users_role
    if role:
        conditions.append("LOWER(role) = %s")
        params.append(role)

    # Construire la requête finale
    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += " ORDER BY id DESC LIMIT 500"

    c.execute(query, params)
    users = c.fetchall()
    conn.close()

    return render_template('admin/admin_users.html', 
                         users=users, 
                         new_notifications_count=get_new_notifications_count(),
                         active="users")

@app.route('/admin/users/export')
@require_admin
def export_users():
    """Export des utilisateurs filtrés/recherchés au format Excel"""
    q = request.args.get('q', '').strip().lower()
    role_filter = request.args.get('role')

    conn = get_db()
    c = conn.cursor()

    query = "SELECT id, name, email, role, create_date FROM users WHERE 1=1"
    params = []

    if q:
        query += """ AND (
            CAST(id AS TEXT) LIKE ? OR
            LOWER(name) LIKE ? OR
            LOWER(email) LIKE ? OR
            LOWER(role) LIKE ? OR
            LOWER(create_date) LIKE ?
        )"""
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])

    if role_filter:
        query += " AND role = ?"
        params.append(role_filter)

    query += " ORDER BY id DESC"

    c.execute(query, params)
    users = c.fetchall()
    conn.close()

    # Création fichier Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Utilisateurs"
    ws.append(["ID", "Nom", "Email", "Rôle", "Date d'inscription"])

    for u in users:
        ws.append(u)

    # Création d'un fichier temporaire
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_path = temp_file.name
    temp_file.close()

    wb.save(temp_path)

    return send_file(
        temp_path,
        as_attachment=True,
        download_name="utilisateurs_export.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route('/admin/user/<int:user_id>/role', methods=['POST'])
@require_admin
def update_user_role(user_id):
    """Changer le rôle d'un utilisateur depuis le dropdown POST"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    valid_roles = ['user', 'admin', 'partenaire']
    
    role = request.form.get('role')
    if role not in valid_roles:
        flash("Rôle invalide.")
        return redirect(url_for('admin_users'))
    
    conn = get_db()
    c = conn.cursor()
    
    # Ne pas laisser supprimer l'admin principal
    # MULTI-TENANT: Filtrer par tenant_id
    c.execute(adapt_query("SELECT email FROM users WHERE id=? AND tenant_id=?"), (user_id, tenant_id))
    user = c.fetchone()
    
    if user:
        user_email = user.get('email') if isinstance(user, dict) else user[0]
        if user_email == 'coco.cayre@gmail.com' and role != 'admin':
            flash("Impossible de retirer le rôle admin à l'administrateur principal.")
            conn.close()
            return redirect(url_for('admin_users'))
    
    # MULTI-TENANT: Ajouter tenant_id au WHERE
    c.execute(adapt_query("UPDATE users SET role=? WHERE id=? AND tenant_id=?"), (role, user_id, tenant_id))
    conn.commit()
    conn.close()
    
    flash(f"Rôle de l'utilisateur mis à jour : {role}")
    return redirect(url_for('admin_users'))


@app.route('/admin/send_email_role', methods=['POST'])
@require_admin
def send_email_role():
    role = request.form.get('role')
    subject = request.form.get('subject')
    message_body = request.form.get('message')

    if role not in ['user', 'partenaire']:
        flash("Rôle invalide.")
        return redirect(url_for('admin_users'))

    if not subject or not message_body:
        flash("Objet et message obligatoires.")
        return redirect(url_for('admin_users'))

    # --- Récupérer tous les emails ---
    conn = get_db()
    c = conn.cursor()
    c.execute(adapt_query("SELECT email FROM users WHERE role=?"), (role,))
    emails = [
        (row.get('email') if isinstance(row, dict) else row[0]) 
        for row in c.fetchall()
    ]
    conn.close()

    if not emails:
        flash(f"Aucun {role} trouvé pour l'envoi.")
        return redirect(url_for('admin_users'))

    # --- Configuration SMTP Gmail ---
    SMTP_SERVER = get_setting("smtp_server") or "smtp.gmail.com"
    SMTP_PORT = int(get_setting("smtp_port") or 587)
    SMTP_USER = get_setting("email_sender") or "coco.cayre@gmail.com"
    SMTP_PASSWORD = get_setting("smtp_password") or "motdepassepardefaut"

    # HTML du mail
    # HTML du mail avec design similaire à ton site
    html_template = f"""
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="background:#f4f5f7; margin:0; padding:0;">
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width:600px; margin:40px auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background:#1E3A8A; color:#fff; padding:20px; text-align:center;">
                <h1 style="margin:0; font-size:22px;">{subject}</h1>
            </div>
            
            <!-- Body -->
            <div style="padding:25px; color:#333; font-size:15px; line-height:1.6;">
                <p>{message_body}</p>
                <p>Vous recevez cet email car vous êtes <strong>{role}</strong> sur notre plateforme.</p>
                
                <!-- Bouton -->
                <div style="text-align:center; margin:25px 0;">
                    <a href="https://www.tonsite.com" 
                    style="background:#1E3A8A; color:#fff; text-decoration:none; padding:10px 20px; border-radius:6px; display:inline-block; font-weight:bold;">
                        Accéder au site
                    </a>
                </div>
                
                <p style="font-size:12px; color:#777;">Merci de ne pas répondre directement à cet email.</p>
            </div>
            
            <!-- Footer -->
            <div style="background:#f0f2f5; padding:15px; text-align:center; font-size:12px; color:#777;">
                © {datetime.now().year} VotreSite. Tous droits réservés.
            </div>
        </div>
    </body>
    </html>
    """

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)

        for email in emails:
            msg = MIMEMultipart('alternative')
            msg['From'] = SMTP_USER
            msg['To'] = email
            msg['Subject'] = Header(subject, 'utf-8')
            msg.attach(MIMEText(html_template, 'html', 'utf-8'))

            # Envoi en bytes pour éviter l'erreur ASCII
            server.sendmail(SMTP_USER, email, msg.as_bytes())

        server.quit()
        flash(f"Emails HTML envoyés à tous les {role}s ({len(emails)} destinataires).")

    except Exception as e:
        flash(f"Erreur lors de l'envoi : {e}")

    return redirect(url_for('admin_users'))

# --------------------------------
# EMAIL DE CONFIRMATION DE COMMANDE
# --------------------------------

def send_order_email(customer_email, customer_name, order_id, total_price, items):
    """
    Envoie un email de confirmation de commande au client avec design moderne du site.
    """
    # --- CONFIGURATION SMTP DYNAMIQUE ---
    SMTP_SERVER = get_setting("smtp_server") or "smtp.gmail.com"
    SMTP_PORT = int(get_setting("smtp_port") or 587)
    SMTP_USER = get_setting("email_sender") or "coco.cayre@gmail.com"
    SMTP_PASSWORD = get_setting("smtp_password") or "motdepassepardefaut"
    color_primary = get_setting("color_primary") or "#6366f1"
    
    # --- CONSTRUCTION DU MESSAGE ---
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = customer_email
    msg['Subject'] = f"✅ Confirmation de votre commande #{order_id}"

    # Génération de la liste des articles
    items_html = ""
    for i, item in enumerate(items):
        cid = f"item{i}"
        
        # Extract item fields safely
        if isinstance(item, dict):
            item_name = item.get('name', 'Produit')
            item_image = item.get('image', '')
            item_quantity = item.get('quantity', 1)
            item_price = item.get('price', 0)
        else:
            item_name = item[1]
            item_image = item[2]
            item_quantity = item[4]
            item_price = item[3]
        
        image_path = os.path.join("static", item_image)
        items_html += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 15px 10px;">
                <img src="cid:{cid}" alt="{item_name}" style="
                    width: 80px;
                    height: 80px;
                    object-fit: cover;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                ">
            </td>
            <td style="padding: 15px 10px;">
                <strong style="color: #1a1a1a; font-size: 15px;">{item_name}</strong><br>
                <span style="color: #666; font-size: 14px;">Quantité : {item_quantity}</span>
            </td>
            <td style="padding: 15px 10px; text-align: right;">
                <strong style="color: {color_primary}; font-size: 16px;">{item_price} €</strong>
            </td>
        </tr>
        """
        # Attacher l'image
        if os.path.exists(image_path):
            with open(image_path, 'rb') as img_file:
                img = MIMEImage(img_file.read())
                img.add_header('Content-ID', f'<{cid}>')
                img.add_header('Content-Disposition', 'inline', filename=os.path.basename(image_path))
                msg.attach(img)

    track_url = f"http://127.0.0.1:5000/order/{order_id}"

    # Contenu de l'email
    content = f"""
    <p style="font-size: 16px; margin-bottom: 20px;">Bonjour <strong>{customer_name}</strong>,</p>
    
    <p>Merci pour votre confiance ! Votre commande <strong>#{order_id}</strong> a bien été enregistrée. 🎉</p>
    
    <div style="
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        margin: 25px 0;
    ">
        <h3 style="margin: 0 0 20px 0; color: #1a1a1a; font-size: 18px;">📦 Détail de votre commande</h3>
        <table style="width: 100%; border-collapse: collapse;">
            {items_html}
        </table>
        
        <div style="
            text-align: right;
            margin-top: 20px;
            padding-top: 15px;
            border-top: 2px solid {color_primary};
        ">
            <span style="font-size: 14px; color: #666;">Total</span><br>
            <strong style="font-size: 24px; color: {color_primary};">{total_price} €</strong>
        </div>
    </div>
    
    <div style="
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
        border-left: 4px solid {color_primary};
        padding: 20px;
        border-radius: 8px;
        margin: 25px 0;
    ">
        <p style="margin: 0; font-size: 14px; color: #444;">
            <strong>📍 Prochaines étapes :</strong><br>
            • Votre commande est en cours de traitement<br>
            • Vous recevrez un email dès l'expédition<br>
            • Suivez l'état de votre commande en temps réel
        </p>
    </div>
    """
    
    html_body = generate_email_html(
        title=f"Commande #{order_id} confirmée",
        content=content,
        button_text="🔍 Suivre ma commande",
        button_url=track_url
    )
    
    msg.attach(MIMEText(html_body, 'html'))

    # --- ENVOI ---
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email envoyé avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")

@app.route('/dynamic-colors.css')
def dynamic_colors():
    """Génère dynamiquement le CSS des couleurs du site"""
    try:
        # Use a template file to render dynamic color tokens
        settings = {
            'primary_color': get_setting("primary_color"),
            'secondary_color': get_setting("secondary_color"),
            'accent_color': get_setting("accent_color"),
            'button_text_color': get_setting("button_text_color"),
            'content_text_color': get_setting("content_text_color"),
            'button_hover_color': get_setting("button_hover_color"),
            'background_color': get_setting("background_color"),
            'success_color': get_setting("success_color"),
            'warning_color': get_setting("warning_color"),
            'error_color': get_setting("error_color"),
            'muted_color': get_setting("muted_color"),
            'surface_color': get_setting("surface_color"),
        }

        css = render_template('dynamic_colors.css.j2', settings=settings)
        # ETag for client caching
        import hashlib
        etag = hashlib.sha1(css.encode('utf-8')).hexdigest()
        if_none = request.headers.get('If-None-Match')
        if if_none == etag:
            return '', 304

        response = make_response(css)
        response.mimetype = 'text/css'
        # Cache for a short period; admin updates invalidate via set_setting cache invalidation
        response.headers['Cache-Control'] = 'public, max-age=300'
        response.headers['ETag'] = etag
        return response
    except Exception as e:
        print(f"[DYNAMIC_COLORS] Erreur génération CSS couleurs: {e}")
        return "", 500

# Correction du décorateur require_api_key pour accepter la clé API en header ou paramètre GET
from functools import wraps

# Note: The main require_api_key decorator is defined near the beginning of the API section
# It uses constant-time comparison with hmac.compare_digest for security


@app.route('/api/export/full', methods=['GET'])
@require_api_key
def api_export_full():
    """
    Exporte TOUTES les données du site en JSON
    Headers requis: X-API-Key
    """
    try:
        conn = get_db()
        cur = conn.cursor()
        
        data = {}
        
        # Exporter toutes les tables
        for table_name in TABLES.keys():
            try:
                cur.execute(adapt_query(f"SELECT * FROM {table_name}"))
                rows = cur.fetchall()
                
                # Convertir en liste de dictionnaires
                data[table_name] = convert_rows_to_dicts(rows, cur.description) if rows else []
            except Exception as e:
                print(f"Erreur lors de l'export de {table_name}: {e}")
                data[table_name] = []
        
        conn.close()
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "tables_count": len(data),
            "total_records": sum(len(v) for v in data.values())
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/orders', methods=['GET'])
@require_api_key
def api_orders():
    """Récupère toutes les commandes au format dashboard - OPTIMISÉ - MULTI-TENANT: filtré par tenant_id"""
    try:
        # MULTI-TENANT: Récupérer le tenant_id basé sur le host
        tenant_id = get_current_tenant_id()
        
        conn = get_db()
        cur = conn.cursor()
        
        # OPTIMISÉ: Colonnes spécifiques + LIMIT pour pagination
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # MULTI-TENANT: Filtrer par tenant_id
        cur.execute(adapt_query("""
            SELECT id, customer_name, email, total_price, order_date, status 
            FROM orders 
            WHERE tenant_id = ?
            ORDER BY order_date DESC
            LIMIT %s OFFSET %s
        """), (tenant_id, limit, offset))
        orders_rows = cur.fetchall()
        orders = convert_rows_to_dicts(orders_rows, cur.description)
        
        # OPTIMISÉ: Récupérer tous les items en une seule requête JOIN
        # MULTI-TENANT: Filtrer order_items et paintings par tenant_id
        order_ids = [o['id'] for o in orders]
        if order_ids:
            placeholders = ','.join(['%s'] * len(order_ids))
            # MULTI-TENANT: Double vérification - order_items et paintings doivent appartenir au tenant
            cur.execute(f"""
                SELECT oi.order_id, oi.painting_id, p.name, p.image, oi.price, oi.quantity
                FROM order_items oi
                LEFT JOIN paintings p ON oi.painting_id = p.id AND p.tenant_id = %s
                WHERE oi.order_id IN ({placeholders}) AND oi.tenant_id = %s
            """, [tenant_id] + order_ids + [tenant_id])
            all_items = cur.fetchall()
            
            # Grouper les items par order_id
            items_by_order = {}
            for item in all_items:
                order_id = safe_row_get(item, 'order_id', index=0)
                if order_id not in items_by_order:
                    items_by_order[order_id] = []
                items_by_order[order_id].append({
                    'painting_id': safe_row_get(item, 'painting_id', index=1),
                    'name': safe_row_get(item, 'name', index=2),
                    'image': safe_row_get(item, 'image', index=3),
                    'price': safe_row_get(item, 'price', index=4),
                    'quantity': safe_row_get(item, 'quantity', index=5)
                })
            
            # Assigner les items à chaque commande
            for order in orders:
                order['items'] = items_by_order.get(order['id'], [])
                order['site_name'] = get_setting("site_name") or "Site Artiste"
        
        conn.close()
        return jsonify({"orders": orders, "count": len(orders)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/users', methods=['GET'])
@require_api_key
def api_users():
    """Récupère tous les utilisateurs au format dashboard - OPTIMISÉ - MULTI-TENANT: filtré par tenant_id"""
    try:
        # MULTI-TENANT: Récupérer le tenant_id basé sur le host
        tenant_id = get_current_tenant_id()
        
        conn = get_db()
        cur = conn.cursor()
        
        # OPTIMISÉ: Colonnes spécifiques + pagination
        # MULTI-TENANT: Filtrer par tenant_id
        limit = request.args.get('limit', 500, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        cur.execute(adapt_query("""
            SELECT id, name, email, create_date, role
            FROM users
            WHERE tenant_id = ?
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """), (tenant_id, limit, offset))
        rows = cur.fetchall()
        users = convert_rows_to_dicts(rows, cur.description)
        
        site_name = get_setting("site_name") or "Site Artiste"
        for user in users:
            user["site_name"] = site_name
        
        conn.close()
        return jsonify({"users": users, "count": len(users)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/paintings', methods=['GET'])
@require_api_key
def api_paintings():
    """Récupère toutes les peintures au format dashboard - OPTIMISÉ - MULTI-TENANT: filtré par tenant_id"""
    try:
        # MULTI-TENANT: Récupérer le tenant_id basé sur le host
        tenant_id = get_current_tenant_id()
        
        conn = get_db()
        cur = conn.cursor()
        
        # OPTIMISÉ: Colonnes spécifiques + pagination
        # MULTI-TENANT: Filtrer par tenant_id
        limit = request.args.get('limit', 200, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        cur.execute(adapt_query("""
            SELECT id, name, price, category, technique, year, quantity, status, image, display_order
            FROM paintings 
            WHERE tenant_id = ?
            ORDER BY display_order DESC, id DESC
            LIMIT %s OFFSET %s
        """), (tenant_id, limit, offset))
        rows = cur.fetchall()
        paintings = convert_rows_to_dicts(rows, cur.description)
        
        site_name = get_setting("site_name") or "Site Artiste"
        for painting in paintings:
            painting["site_name"] = site_name
        
        conn.close()
        return jsonify({"paintings": paintings, "count": len(paintings)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/exhibitions', methods=['GET'])
@require_api_key
def api_exhibitions():
    """Récupère toutes les expositions au format dashboard"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    try:
        conn = get_db()
        cur = conn.cursor()
        # MULTI-TENANT: Filtrer par tenant_id
        cur.execute(adapt_query("SELECT id, title, location, date, start_time, end_time, description FROM exhibitions WHERE tenant_id=? ORDER BY date DESC"), (tenant_id,))
        rows = cur.fetchall()
        exhibitions = convert_rows_to_dicts(rows, cur.description)
        site_name = get_setting("site_name") or "Site Artiste"
        for exhibition in exhibitions:
            exhibition["site_name"] = site_name
        conn.close()
        return jsonify({"exhibitions": exhibitions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/custom-requests', methods=['GET'])
@require_api_key
def api_custom_requests():
    """Récupère toutes les demandes personnalisées au format dashboard"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    try:
        conn = get_db()
        cur = conn.cursor()
        # MULTI-TENANT: Filtrer par tenant_id
        cur.execute(adapt_query("SELECT id, client_name, description, status, created_at FROM custom_requests WHERE tenant_id=? ORDER BY created_at DESC"), (tenant_id,))
        rows = cur.fetchall()
        columns = [description[0] for description in cur.description]
        requests_data = [dict(zip(columns, row)) for row in rows]
        site_name = get_setting("site_name") or "Site Artiste"
        for req in requests_data:
            req["site_name"] = site_name
        conn.close()
        return jsonify({"custom_requests": requests_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/settings', methods=['GET'])
@require_api_key
def api_export_settings():
    """Exporte les paramètres (sauf clés sensibles)"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    try:
        conn = get_db()
        cur = conn.cursor()
        # MULTI-TENANT: Filtrer par tenant_id
        cur.execute(adapt_query("SELECT * FROM settings WHERE tenant_id=?"), (tenant_id,))
        rows = cur.fetchall()
        
        # Masquer les clés sensibles
        sensitive_keys = ['stripe_secret_key', 'smtp_password', 'export_api_key']
        
        columns = [description[0] for description in cur.description]
        settings = []
        for row in rows:
            setting = dict(zip(columns, row))
            if setting['key'] in sensitive_keys:
                setting['value'] = '***MASKED***'
            settings.append(setting)
        
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(settings),
            "data": settings
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/stats', methods=['GET'])
@require_api_key
def api_export_stats():
    """Exporte des statistiques générales"""
    # MULTI-TENANT: Récupérer tenant_id
    tenant_id = get_current_tenant_id()
    
    try:
        conn = get_db()
        cur = conn.cursor()
        
        stats = {}
        
        # Compter les enregistrements dans chaque table
        for table_name in TABLES.keys():
            try:
                cur.execute(adapt_query(f"SELECT COUNT(*) as count FROM {table_name}"))
                result = cur.fetchone()
                count = safe_row_get(result, 'count', index=0, default=0)
                stats[f"{table_name}_count"] = count
            except:
                stats[f"{table_name}_count"] = 0
        
        # Statistiques supplémentaires
        # MULTI-TENANT: Filtrer par tenant_id
        try:
            cur.execute(adapt_query("SELECT SUM(total_price) as total FROM orders WHERE tenant_id=?"), (tenant_id,))
            result = cur.fetchone()
            total_revenue = safe_row_get(result, 'total', index=0, default=0) or 0
            stats['total_revenue'] = float(total_revenue)
        except:
            stats['total_revenue'] = 0
        
        try:
            cur.execute(adapt_query("SELECT COUNT(*) as count FROM orders WHERE status = 'Livrée' AND tenant_id=?"), (tenant_id,))
            result = cur.fetchone()
            stats['delivered_orders'] = safe_row_get(result, 'count', index=0, default=0)
        except:
            stats['delivered_orders'] = 0
        
        conn.close()
        
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/export/settings/stripe_publishable_key', methods=['GET'])
def get_stripe_publishable_key():
    """Public endpoint returning only the publishable key for client usage.
    Allows CORS for browser clients. Never returns secret keys.
    Retourne: 200 {"success": true, "publishable_key": "pk_test_..."}
    """
    try:
        pk = get_setting('stripe_publishable_key')
        if not pk:
            pk = os.getenv('STRIPE_PUBLISHABLE_KEY')
        if not pk:
            return jsonify({'success': False, 'error': 'not_found'}), 404

        resp = jsonify({'success': True, 'publishable_key': pk})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET'
        return resp, 200
    except Exception as e:
        try:
            print(f"[API] ❌ Erreur GET stripe_publishable_key: {e}")
        except UnicodeEncodeError:
            print("[API] Erreur GET stripe_publishable_key: %s" % str(e))
        return jsonify({'success': False, 'error': 'internal'}), 500


@app.route('/api/export/settings/stripe_secret_key', methods=['PUT'])
def update_stripe_secret_key():
    """Endpoint dédié pour persister la clé secrète Stripe via l'API export.
    Exige header `X-API-Key` égal à `TEMPLATE_MASTER_API_KEY` (ou export_api_key fallback).
    Body JSON attendu: {"value": "sk_test_..."}
    Réponses:
      - 200 {"success": true, "message": "secret_saved"}
      - 401 {"success": false, "error": "invalid_api_key"}
      - 400 {"success": false, "error": "invalid_secret_format"}
    """
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'success': False, 'error': 'invalid_api_key'}), 401

        # accept master key or previously provisioned export_api_key
        master_key = TEMPLATE_MASTER_API_KEY
        has_valid_master = False
        if api_key and master_key:
            try:
                has_valid_master = hmac.compare_digest(api_key, master_key)
            except Exception:
                has_valid_master = False
        
        if has_valid_master:
            pass
        else:
            stored_key = get_setting('export_api_key')
            if not stored_key:
                # provision a random export key if none exists (keeps backward compatibility)
                stored_key = secrets.token_urlsafe(32)
                set_setting('export_api_key', stored_key)
                print(f"New export_api_key provisioned")
            
            # Always perform constant-time comparison
            has_valid_stored = False
            if api_key and stored_key:
                try:
                    has_valid_stored = hmac.compare_digest(api_key, stored_key)
                except Exception:
                    has_valid_stored = False
            
            if not has_valid_stored:
                return jsonify({'success': False, 'error': 'invalid_api_key'}), 401

        data = request.get_json(silent=True) or {}
        value = data.get('value')
        if not value or not isinstance(value, str):
            return jsonify({'success': False, 'error': 'invalid_secret_format'}), 400

        import re
        if not re.match(r'^sk_(test|live)_[A-Za-z0-9_-]+$', value):
            return jsonify({'success': False, 'error': 'invalid_secret_format'}), 400

        # Persist secret server-side only
        # Store under key 'stripe_secret_key' in settings (never exposed via GET)
        set_setting('stripe_secret_key', value)

        # Masked logging
        masked = value[:6] + '...' + value[-4:]
        try:
            print(f"[API] stripe_secret_key saved: {masked}")
        except UnicodeEncodeError:
            print("[API] stripe_secret_key saved: %s" % masked)

        return jsonify({'success': True, 'message': 'secret_saved'}), 200
    except Exception as e:
        try:
            print(f"[API] Erreur mise à jour stripe_secret_key: {e}")
        except UnicodeEncodeError:
            print("[API] Erreur mise à jour stripe_secret_key: %s" % str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/settings/stripe_publishable_key', methods=['PUT'])
def update_stripe_publishable_key():
    """Endpoint dédié pour persister la clé publishable Stripe via l'API export.
    Auth: priorise TEMPLATE_MASTER_API_KEY, fallback sur export_api_key stockée en settings.
    Corps JSON attendu: {"value": "pk_test_..."}
    """
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'success': False, 'error': 'API key manquante'}), 401

        # Priorité maître - use constant-time comparison
        master_key = TEMPLATE_MASTER_API_KEY
        has_valid_master = False
        if api_key and master_key:
            try:
                has_valid_master = hmac.compare_digest(api_key, master_key)
            except Exception:
                has_valid_master = False
        
        if has_valid_master:
            try:
                print('[API] Clé maître acceptée - Configuration stripe_publishable_key')
            except UnicodeEncodeError:
                print('[API] Clé maître acceptée - Configuration stripe_publishable_key')
        else:
            stored_key = get_setting('export_api_key')
            if not stored_key:
                stored_key = secrets.token_urlsafe(32)
                set_setting('export_api_key', stored_key)
                try:
                    print(f"Nouvelle clé API générée: {stored_key}")
                except UnicodeEncodeError:
                    print("Nouvelle clé API générée: %s" % stored_key)
            
            # Always perform constant-time comparison
            has_valid_stored = False
            if api_key and stored_key:
                try:
                    has_valid_stored = hmac.compare_digest(api_key, stored_key)
                except Exception:
                    has_valid_stored = False
            
            if not has_valid_stored:
                return jsonify({'success': False, 'error': 'Clé API invalide'}), 403

        data = request.get_json() or {}
        value = data.get('value')
        if not value:
            return jsonify({'success': False, 'error': 'Valeur manquante'}), 400

        # Validate publishable key format
        import re
        if not re.match(r'^pk_(test|live)_[A-Za-z0-9_-]+$', value):
            return jsonify({'success': False, 'error': 'invalid_publishable_format'}), 400

        # Persist publishable key (non sensible côté template)
        set_setting('stripe_publishable_key', value)

        # Log with origin info
        try:
            ip = request.remote_addr or 'unknown'
            ua = request.headers.get('User-Agent', '')
            app.logger.info(f"[API] stripe_publishable_key updated from {ip} - UA:{ua}")
        except Exception:
            pass

        return jsonify({'success': True, 'message': 'stripe_publishable_key mis à jour'})

    except Exception as e:
        try:
            print(f"[API] ❌ Erreur mise à jour stripe_publishable_key: {e}")
        except UnicodeEncodeError:
            print("[API] Erreur mise à jour stripe_publishable_key: %s" % str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/settings/stripe_secret_key', methods=['GET'])
def get_stripe_secret_key_blocked():
    """Security: Never expose the secret key to GET requests.
    Secret keys must never be transmitted to clients.
    Retourne: 404 Not Found
    """
    return jsonify({'error': 'not_found'}), 404


@app.route('/api/export/settings/stripe_price_id', methods=['PUT'])
@require_api_key
def update_stripe_price_id():
    """Endpoint pour propager un price_id Stripe du Dashboard au Template.
    
    Utile quand le Dashboard crée des produits Stripe et doit propager les price_id
    aux sites templates (ex: prix de lancement, abonnements centralisés).
    
    Auth: X-API-Key (TEMPLATE_MASTER_API_KEY ou export_api_key)
    Body: {"value": "price_1A4Xc..."}
    """
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'success': False, 'error': 'API key manquante'}), 401

        master_key = TEMPLATE_MASTER_API_KEY
        has_valid_master = False
        if api_key and master_key:
            try:
                has_valid_master = hmac.compare_digest(api_key, master_key)
            except Exception:
                has_valid_master = False
        
        if has_valid_master:
            pass
        else:
            stored_key = get_setting('export_api_key')
            if not stored_key:
                stored_key = secrets.token_urlsafe(32)
                set_setting('export_api_key', stored_key)
            
            has_valid_stored = False
            if api_key and stored_key:
                try:
                    has_valid_stored = hmac.compare_digest(api_key, stored_key)
                except Exception:
                    has_valid_stored = False
            
            if not has_valid_stored:
                return jsonify({'success': False, 'error': 'Clé API invalide'}), 403

        data = request.get_json() or {}
        value = data.get('value')
        if not value or not isinstance(value, str):
            return jsonify({'success': False, 'error': 'price_id manquant'}), 400

        # Validate price_id format (loose: prix_ ou prix_<id>)
        # Stripe price IDs commencent par "price_" suivi d'alphanumériques et traits
        import re
        if not re.match(r'^(price_)?[A-Za-z0-9_]+$', value):
            return jsonify({'success': False, 'error': 'invalid_price_id_format'}), 400

        # Stocker en Supabase
        set_setting('stripe_price_id', value)

        try:
            print(f"[API] stripe_price_id updated: {value[:20]}...")
        except Exception:
            pass

        return jsonify({'success': True, 'message': 'stripe_price_id mis à jour'}), 200

    except Exception as e:
        try:
            print(f"[API] Erreur mise à jour stripe_price_id: {e}")
        except Exception:
            pass
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/settings/stripe_price_id', methods=['GET'])
def get_stripe_price_id():
    """Récupère le price_id Stripe stocké (optionnel, peut être public)."""
    try:
        price_id = get_setting('stripe_price_id')
        if not price_id:
            price_id = os.getenv('STRIPE_PRICE_ID')
        
        if not price_id:
            return jsonify({'success': False, 'error': 'not_found'}), 404
        
        return jsonify({'success': True, 'price_id': price_id}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stripe-pk', methods=['GET'])
def api_stripe_pk():
    """Retourne la clé publishable Stripe au client.
    Logique : 1) lire depuis settings (stripe_publishable_key)
             2) fallback sur variable d'environnement STRIPE_PUBLISHABLE_KEY
             3) fallback server->server : interroger le dashboard central si configuré
    """
    try:
        # 1) lecture locale (BDD)
        pk = get_setting('stripe_publishable_key')
        if pk:
            return jsonify({"success": True, "publishable_key": pk})

        # 2) env var fallback
        pk = os.getenv('STRIPE_PUBLISHABLE_KEY')
        if pk:
            return jsonify({"success": True, "publishable_key": pk})

        # 3) server->server fallback via dashboard
        base_url = get_setting('dashboard_api_base') or os.getenv('DASHBOARD_URL') or 'https://admin.artworksdigital.fr'
        site_id = get_setting('dashboard_id') or os.getenv('SITE_NAME')
        if base_url and site_id:
            try:
                ep = f"{base_url.rstrip('/')}/api/sites/{site_id}/stripe-key"
                resp = requests.get(ep, timeout=6)
                if resp.status_code == 200:
                    data = resp.json() or {}
                    # accept different key names
                    key = data.get('publishable_key') or data.get('stripe_publishable_key') or data.get('stripe_key') or data.get('stripe_publishable')
                    if not key:
                        # older dashboard might return under 'stripe_secret_key' (we must NOT expose secret)
                        key = data.get('publishableKey')
                    if key:
                        return jsonify({"success": True, "publishable_key": key})
            except Exception as e:
                print(f"[SAAS] Erreur fallback Stripe PK depuis dashboard: {e}")

        return jsonify({"success": False, "message": "no_publishable_key"}), 404
    except Exception as e:
        print(f"[SAAS] Erreur endpoint /api/stripe-pk: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/upload/image', methods=['POST'])
@require_api_key
def upload_image():
    """Uploader une image via l'API"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nom de fichier vide'}), 400
    
    # Vérifier l'extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if ext not in allowed_extensions:
        return jsonify({'success': False, 'error': 'Format non autorisé'}), 400
    
    try:
        # Sécuriser le nom de fichier
        filename = secure_filename(file.filename)
        
        # Sauvegarder dans le dossier static/Images
        filepath = os.path.join('static', 'Images', filename)
        file.save(filepath)
        
        # Retourner le chemin relatif
        return jsonify({
            'success': True,
            'path': f'Images/{filename}',
            'filename': filename,
            'message': 'Image uploadée avec succès'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/api-key', methods=['GET'])
@require_admin
def get_export_api_key():
    """
    Récupère ougénère la clé API pour l'export
    Accessible uniquement aux administrateurs connectés
    """
    user_id = session.get('user_id')
    api_key = get_setting("export_api_key", user_id=user_id)
    if not api_key:
        api_key = secrets.token_urlsafe(32)
        set_setting("export_api_key", api_key, user_id=user_id)
    
    return jsonify({
        "success": True,
        "api_key": api_key,
        "usage": "Utilisez cette clé dans le header 'X-API-Key' pour les requêtes d'export"
    })


@app.route('/api/export/regenerate-key', methods=['POST'])
@require_admin
def regenerate_export_api_key():
    """Régénère une nouvelle clé API"""
    new_key = secrets.token_urlsafe(32)
    set_setting("export_api_key", new_key)
    
    return jsonify({
        "success": True,
        "api_key": new_key,
        "message": "Nouvelle clé API générée"
    })


# ================================
# SAAS ARTISTES – WORKFLOW
# ================================

def _get_user_info(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(adapt_query("SELECT id, name, email FROM users WHERE id=?"), (user_id,))
    row = c.fetchone()
    conn.close()
    return row if row else None

def _saas_upsert(user_id, **fields):
    conn = get_db()
    c = conn.cursor()
    # Check existence
    c.execute(adapt_query("SELECT id FROM saas_sites WHERE user_id=?"), (user_id,))
    existing = c.fetchone()
    if existing:
        # Build update dynamically
        keys = list(fields.keys())
        set_clause = ", ".join([f"{k}=?" for k in keys])
        values = [fields[k] for k in keys] + [user_id]
        c.execute(adapt_query(f"UPDATE saas_sites SET {set_clause} WHERE user_id=?"), values)
    else:
        cols = ["user_id"] + list(fields.keys())
        placeholders = ",".join([PARAM_PLACEHOLDER] * len(cols))
        values = [user_id] + [fields[k] for k in fields.keys()]
        c.execute(adapt_query(f"INSERT INTO saas_sites ({','.join(cols)}) VALUES ({placeholders})"), values)
    conn.commit()
    conn.close()

def _send_saas_step_email(user_id, step_name, subject, content):
    try:
        user = _get_user_info(user_id)
        if not user:
            print(f"[DEBUG] Step: Email SKIP | UserID: {user_id} | Reason: user_not_found")
            return
        _, user_name, user_email = user
        email_sender = get_setting("email_sender") or "contact@example.com"
        smtp_password = get_setting("smtp_password")
        smtp_server = get_setting("smtp_server") or "smtp.gmail.com"
        smtp_port = int(get_setting("smtp_port") or 587)

        html_body = generate_email_html(
            title=subject,
            content=content,
            button_text=None,
            button_url=None
        )

        if smtp_password:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg['From'] = email_sender
            msg['To'] = user_email
            msg['Subject'] = subject
            msg.attach(MIMEText(html_body, 'html'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_sender, smtp_password)
            server.send_message(msg)
            server.quit()

        print(f"[DEBUG] Step: Email envoyé | UserID: {user_id} | Step: {step_name}")
    except Exception as e:
        print(f"[DEBUG] Step: Email erreur | UserID: {user_id} | Step: {step_name} | Err: {e}")

@app.route('/saas/apply', methods=['POST'])
def saas_apply():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401
    _saas_upsert(user_id, status='pending_approval')
    print(f"[DEBUG] Step: Formulaire rempli | UserID: {user_id} | Status: pending_approval")
    _send_saas_step_email(user_id, 'pending_approval', 'Formulaire reçu', 'Votre demande a été enregistrée. En attente d\'approbation.')
    return jsonify({"ok": True, "status": "pending_approval"})

@app.route('/saas/approve/<int:user_id>', methods=['POST'])
@require_admin
def saas_approve(user_id):
    sandbox_url = f"https://sandbox-projetjb-{user_id}.onrender.com"
    _saas_upsert(user_id, status='approved', sandbox_url=sandbox_url)
    print(f"[DEBUG] Step: Sandbox créé | UserID: {user_id} | Domain: {sandbox_url}")
    print(f"[DEBUG] Preview → API désactivée | UserID: {user_id}")
    _send_saas_step_email(user_id, 'approved', 'Sandbox créé', f"Votre espace de prévisualisation est prêt: {sandbox_url}")
    return jsonify({"ok": True, "status": "approved", "sandbox_url": sandbox_url})

@app.route('/saas/paid/<int:user_id>', methods=['POST'])
@require_admin
def saas_paid(user_id):
    _saas_upsert(user_id, status='paid')
    print(f"[DEBUG] Step: Paiement Stripe validé | UserID: {user_id} | Status: paid")
    _send_saas_step_email(user_id, 'paid', 'Paiement confirmé', "Votre paiement a été validé. Nous poursuivons la mise en ligne.")
    return jsonify({"ok": True, "status": "paid"})

@app.route('/saas/domain/<int:user_id>', methods=['POST'])
@require_admin
def saas_domain_verified(user_id):
    final_domain = (request.json or {}).get('final_domain')
    if not final_domain:
        return jsonify({"error": "final_domain requis"}), 400
    _saas_upsert(user_id, status='domain_verified', final_domain=final_domain)
    print(f"[DEBUG] Step: Domaine vérifié | UserID: {user_id} | Domain: {final_domain}")
    _send_saas_step_email(user_id, 'domain_verified', 'Domaine vérifié', f"Votre domaine {final_domain} a été validé.")
    return jsonify({"ok": True, "status": "domain_verified", "final_domain": final_domain})

@app.route('/saas/clone/<int:user_id>', methods=['POST'])
@require_admin
def saas_clone_to_prod(user_id):
    # Ici, on simule le clonage; dans un vrai setup on copierait DB/fichiers
    info = _get_user_info(user_id)
    print(f"[DEBUG] Step: Site cloné en prod | UserID: {user_id} | Domain: {(get_setting('site_name') or 'Projet_JB')} | Status: site_created")
    _saas_upsert(user_id, status='site_created')
    _send_saas_step_email(user_id, 'site_created', 'Site cloné en production', "Votre site a été cloné en production. Activation en cours.")
    return jsonify({"ok": True, "status": "site_created"})

@app.route('/saas/activate/<int:user_id>', methods=['POST'])
@require_admin
def saas_activate(user_id):
    # Production: SSL + API activée (on log uniquement pour ne rien casser)
    print(f"[DEBUG] Step: Site actif en prod | UserID: {user_id} | Status: active")
    print(f"[DEBUG] Production → API activée | UserID: {user_id}")
    _saas_upsert(user_id, status='active')
    _send_saas_step_email(user_id, 'active', 'Site activé', "Votre site est maintenant actif en production.")
    return jsonify({"ok": True, "status": "active"})


@app.route('/saas/launch-site')
def saas_launch_site():
    """Crée une session Stripe pour lancer le site depuis le mode preview."""
    # Vérifier l'authentification
    user_id = session.get('user_id')
    if not user_id:
        flash("Vous devez être connecté pour lancer votre site.")
        return redirect(url_for('login'))
    
    # Sauvegarder le domaine preview actuel pour suppression ultérieure
    preview_host = request.host
    if is_preview_request():
        try:
            set_setting("preview_domain", preview_host, user_id=user_id)
            print(f"[SAAS] Domaine preview {preview_host} sauvegardé pour user_id {user_id}")
        except Exception as e:
            print(f"[SAAS] Erreur sauvegarde preview_domain: {e}")
    
    price = fetch_dashboard_site_price()
    if not price or price <= 0:
        flash("Prix indisponible pour le lancement.")
        return redirect(url_for('home'))

    stripe_secret = get_stripe_secret_key()
    if not stripe_secret:
        flash("Stripe n'est pas configuré.")
        return redirect(url_for('home'))
    stripe.api_key = stripe_secret

    success_url = url_for('saas_launch_success', _external=True)
    cancel_url = request.referrer or url_for('home', _external=True)

    try:
        session_obj = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': 'Lancement de votre site'},
                    'unit_amount': int(price * 100)
                },
                'quantity': 1
            }],
            mode='payment',
            success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=cancel_url,
            metadata={
                'site_id': str(get_setting('dashboard_id') or ''),
                'user_id': str(user_id),
                'context': 'saas_launch'
            }
        )
        print(f"[SAAS] Session Stripe créée | user_id: {user_id} | session_id: {session_obj.id}")
        return redirect(session_obj.url, code=303)
    except Exception as e:
        print(f"[SAAS] Erreur création session Stripe: {e}")
        import traceback
        traceback.print_exc()
        flash("Impossible de lancer la session de paiement pour le moment.")
        return redirect(url_for('home'))


@app.route('/saas/launch/success')
def saas_launch_success():
    # Récupérer l'user_id depuis la session ou la métadonnée Stripe
    user_id = session.get('user_id')
    print(f"[SAAS] DEBUG 1 - user_id from session: {user_id}")
    
    # Si pas en session, récupérer depuis la session Stripe
    if not user_id:
        session_id = request.args.get('session_id')
        print(f"[SAAS] DEBUG 2 - session_id from URL: {session_id}")
        if session_id:
            try:
                stripe_secret = get_stripe_secret_key()
                print(f"[SAAS] DEBUG 3 - stripe_secret available: {bool(stripe_secret)}")
                if stripe_secret:
                    stripe.api_key = stripe_secret
                    session_obj = stripe.checkout.Session.retrieve(session_id)
                    print(f"[SAAS] DEBUG 4 - session_obj metadata: {session_obj.metadata}")
                    user_id = session_obj.metadata.get('user_id') if session_obj.metadata else None
                    print(f"[SAAS] DEBUG 5 - user_id from metadata: {user_id}")
                    user_id = int(user_id) if user_id and str(user_id).isdigit() else None
                    print(f"[SAAS] DEBUG 6 - user_id converted to int: {user_id}")
            except Exception as e:
                print(f"[SAAS] Erreur récupération metadata Stripe: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"[SAAS] DEBUG 7 - final user_id: {user_id}")
    if not user_id:
        flash("Erreur: utilisateur non identifié.")
        return redirect(url_for('home'))
    
    # Initialiser la DB du site si elle n'existe pas
    try:
        init_database(user_id=user_id)
        print(f"[SAAS] DB initialisée pour le site {user_id}")
    except Exception as e:
        print(f"[SAAS] Erreur initialisation DB site: {e}")
    
    # Générer une clé API unique pour ce site
    api_key = secrets.token_urlsafe(32)
    set_setting("export_api_key", api_key, user_id=user_id)
    
    # Rendre le template avec popup pour domaine
    return render_template('saas_launch_success.html', 
                         api_key=api_key, 
                         user_id=user_id)


@app.route('/api/saas/register-site', methods=['POST'])
def api_register_site_saas():
    """Enregistre le site au dashboard et lance le déploiement"""
    data = request.get_json() or {}
    user_id = data.get('user_id') or session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "unauthorized"}), 401
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "user_id invalide"}), 400
    
    domain = data.get('domain', '').strip()
    api_key = data.get('api_key', '').strip()
    
    if not domain or not api_key:
        return jsonify({"error": "domain et api_key requis"}), 400
    
    try:
        # Construire l'URL complète du domaine
        domain_clean = domain.replace('https://', '').replace('http://', '')
        site_url = f"https://{domain_clean}"
        
        # Récupérer le nom du site
        site_name = get_setting("site_name") or "Site Artiste"
        user_info = _get_user_info(user_id)
        user_email = None
        if user_info:
            _, user_name, user_email = user_info
            site_name = user_name or site_name
        
        # Préparer les données pour le dashboard
        dashboard_data = {
            "site_name": site_name,
            "site_url": site_url,
            "api_key": api_key,
            "auto_registered": True,
            "artist_id": user_id
        }
        
        # Envoyer au dashboard
        dashboard_url = f"{get_dashboard_base_url()}/api/sites/register"
        response = requests.post(dashboard_url, json=dashboard_data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            site_id = result.get("site_id", user_id)
            
            # Initialiser la base de données séparée du site
            try:
                init_database(user_id=user_id)
                print(f"[SAAS] DB initialisée pour le site {user_id}")
            except Exception as e:
                print(f"[SAAS] Erreur initialisation DB site: {e}")
            
            # Mettre à jour le statut local
            _saas_upsert(user_id, status='active', final_domain=site_url)
            set_setting("dashboard_id", str(site_id), user_id=user_id)
            set_setting("export_api_key", api_key, user_id=user_id)
            
            # Définir le créateur du site comme administrateur
            if user_email:
                try:
                    set_admin_user(user_email)
                    print(f"[SAAS] User {user_email} défini comme administrateur")
                except Exception as e:
                    print(f"[SAAS] Erreur lors de la définition de l'administrateur: {e}")
            
            # Vérifier que les clés Stripe du preview sont disponibles en production
            try:
                stripe_pk = get_setting('stripe_publishable_key')
                stripe_sk = get_stripe_secret_key()
                print(f"[SAAS] Site {user_id} lancé - Clés Stripe disponibles:")
                print(f"[SAAS]   - Publishable key: {stripe_pk[:20] + '...' if stripe_pk else 'NOT SET'}")
                print(f"[SAAS]   - Secret key: {'SET' if stripe_sk else 'NOT SET'}")
            except Exception as e:
                print(f"[SAAS] Erreur vérification clés Stripe: {e}")
            
            # Supprimer le site preview du dashboard
            try:
                preview_domain_to_delete = get_setting("preview_domain")
                if preview_domain_to_delete:
                    delete_url = f"{get_dashboard_base_url()}/api/sites/delete-preview"
                    delete_response = requests.post(
                        delete_url,
                        json={"artist_id": user_id, "preview_domain": preview_domain_to_delete},
                        timeout=10
                    )
                    if delete_response.status_code == 200:
                        print(f"[SAAS] Site preview {preview_domain_to_delete} supprimé")
                    else:
                        print(f"[SAAS] Erreur suppression preview: {delete_response.status_code}")
            except Exception as e:
                print(f"[SAAS] Erreur lors de la suppression du site preview: {e}")
            
            # Envoyer email de confirmation
            _send_saas_step_email(user_id, 'active', 
                                'Site activé !', 
                                f"Votre site est maintenant actif sur {site_url}")
            
            return jsonify({
                "ok": True,
                "message": "Site enregistré et activé",
                "site_url": site_url,
                "api_key": api_key
            }), 200
        else:
            return jsonify({
                "error": f"Erreur dashboard: {response.status_code}",
                "details": response.text
            }), response.status_code
    
    except Exception as e:
        print(f"[SAAS] Erreur enregistrement site: {e}")
        return jsonify({"error": str(e)}), 500


# ================================
# AUTO-REGISTRATION AU CHARGEMENT DU MODULE
# (Compatible avec Gunicorn)
# ================================

def init_auto_registration():
    """
    Initialise l'auto-registration au chargement du module.
    S'exécute avec Flask dev server ET avec Gunicorn.
    """
    import threading
    import time
    
    # Sécuriser l'activation au démarrage: activer si variable d'env présente
    try:
        env_override = (os.getenv("ENABLE_AUTO_REGISTRATION", "").strip().lower() in ("true", "1", "yes"))
        current = get_setting("enable_auto_registration")
        if env_override:
            set_setting("enable_auto_registration", "true")
            print("[AUTO-REG] ✅ Activation via ENABLE_AUTO_REGISTRATION=true")
        elif current is None:
            # Défaut sûr: activer si le paramètre n'existe pas
            set_setting("enable_auto_registration", "true")
            print("[AUTO-REG] ✅ Activation par défaut de enable_auto_registration (paramètre manquant)")
    except Exception as e:
        print(f"[AUTO-REG] ⚠️ Impossible de forcer l'activation: {e}")
    
    def register_async():
        """Enregistrement asynchrone pour ne pas bloquer le démarrage"""
        time.sleep(2)  # Attendre que l'app soit prête
        
        with app.app_context():
            try:
                print("[AUTO-REG] 🚀 Démarrage auto-registration...")
                register_site_to_dashboard()
            except Exception as e:
                print(f"[AUTO-REG] ⚠️ Erreur globale: {e}")
    
    # Lancer dans un thread daemon pour ne pas bloquer
    thread = threading.Thread(target=register_async, daemon=True)
    thread.start()
    print("[AUTO-REG] Thread de registration lancé")

# Exécuter l'auto-registration au chargement du module
# (fonctionne avec 'python app.py' ET 'gunicorn app:app')
init_auto_registration()

# --------------------------------
# LANCEMENT DE L'APPLICATION
# --------------------------------
if __name__ == "__main__":
    # Mode développement local uniquement
    app.run(debug=True)
