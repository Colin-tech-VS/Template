# --------------------------------
# IMPORTS
# --------------------------------
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, send_file, abort, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from functools import wraps
import os
import smtplib
import uuid
import secrets
import tempfile
import stripe
import json
import requests
import urllib.parse
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

# Import du module de base de données
from database import (
    get_db, 
    get_db_connection, 
    execute_query, 
    create_table_if_not_exists,
    add_column_if_not_exists,
    adapt_query,
    IS_POSTGRES,
    PARAM_PLACEHOLDER
)


# --------------------------------
# CONFIGURATION
# --------------------------------
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

# Dossiers de stockage
app.config['UPLOAD_FOLDER'] = 'static/Images'        # pour les peintures
app.config['EXPO_UPLOAD_FOLDER'] = 'static/expo_images'  # pour les exhibitions

# Extensions autorisées (communes aux deux)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Vérification d'extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_order_by_id(order_id):
    conn = get_db()
    cursor = conn.cursor()
    query = adapt_query("SELECT * FROM orders WHERE id = ?")
    cursor.execute(query, (order_id,))
    order = cursor.fetchone()
    conn.close()
    return order

def get_order_items(order_id):
    conn = get_db()
    cursor = conn.cursor()
    query = adapt_query("SELECT * FROM order_items WHERE order_id = ?")
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
    "paintings": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
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
        "display_order": "INTEGER DEFAULT 0"
    },
    "orders": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "customer_name": "TEXT NOT NULL",
        "email": "TEXT NOT NULL",
        "address": "TEXT NOT NULL DEFAULT ''",
        "total_price": "REAL NOT NULL DEFAULT 0",
        "order_date": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "status": "TEXT NOT NULL DEFAULT 'En cours'",
        "user_id": "INTEGER"
    },
    "order_items": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "order_id": "INTEGER NOT NULL",
        "painting_id": "INTEGER NOT NULL",
        "quantity": "INTEGER NOT NULL",
        "price": "REAL NOT NULL"
    },
    "cart_items": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "cart_id": "INTEGER NOT NULL",
        "painting_id": "INTEGER NOT NULL",
        "quantity": "INTEGER NOT NULL"
    },
    "carts": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "session_id": "TEXT NOT NULL UNIQUE",
        "user_id": "INTEGER"
    },
    "notifications": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "user_id": "INTEGER",
        "message": "TEXT NOT NULL",
        "type": "TEXT NOT NULL",
        "url": "TEXT",
        "is_read": "INTEGER NOT NULL DEFAULT 0",
        "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
    },
    "exhibitions": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
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
        "create_date": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
    },
    "custom_requests": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
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
        "admin_notes": "TEXT"
    },
    # Nouvelle table settings pour stocker toutes les clés API et configs
    "settings": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "key": "TEXT UNIQUE NOT NULL",
        "value": "TEXT NOT NULL"
    },
    # Table SAAS: suivi du cycle de vie des sites artistes
    "saas_sites": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "user_id": "INTEGER UNIQUE",
        "status": "TEXT NOT NULL DEFAULT 'pending_approval'",
        "sandbox_url": "TEXT",
        "final_domain": "TEXT",
        "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
    }
}

# Fonction utilitaire pour récupérer une clé depuis settings
def get_setting(key):
    conn = get_db()
    cur = conn.cursor()
    query = adapt_query("SELECT value FROM settings WHERE key = ?")
    cur.execute(query, (key,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row['value'] if IS_POSTGRES else row["value"]
    return None

stripe_key = get_setting("stripe_secret_key")
masked_stripe = (stripe_key[:6] + "…") if stripe_key else "None"
print("Clé Stripe actuelle (masquée) :", masked_stripe)
# Configurer Stripe si la clé est disponible
if stripe_key:
    stripe.api_key = stripe_key
else:
    print("Stripe non configuré: aucune clé fournie")

# Vérifier les valeurs SMTP
smtp_server = get_setting("smtp_server") or "smtp.gmail.com"
smtp_port = int(get_setting("smtp_port") or 587)
smtp_user = get_setting("email_sender") or "coco.cayre@gmail.com"
smtp_password = get_setting("smtp_password") or "motdepassepardefaut"

print("SMTP_SERVER :", smtp_server)
print("SMTP_PORT   :", smtp_port)
print("SMTP_USER   :", smtp_user)
print("SMTP_PASSWORD défini :", bool(get_setting("smtp_password")))

google_places_key = get_setting("google_places_key") or "CLE_PAR_DEFAUT"
print("Google Places Key utilisée :", google_places_key)

# Fonction utilitaire pour mettre à jour ou créer une clé
def set_setting(key, value):
    conn = get_db()
    cur = conn.cursor()
    query = adapt_query("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """)
    cur.execute(query, (key, value))
    conn.commit()
    conn.close()


# Prévisualisation / Dashboard helpers
def get_dashboard_base_url():
    return (get_setting("dashboard_api_base") or "https://admin.artworksdigital.fr").rstrip("/")


def is_preview_request():
    host = (request.host or "").lower()
    return (
        host.endswith(".preview.artworksdigital.fr")
        or ".preview." in host
        or host.startswith("preview.")
        or "sandbox" in host
    )


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
            resp = requests.get(ep, timeout=8)
            if resp.status_code != 200:
                continue
            data = resp.json() or {}
            base_price = float(data.get("price") or data.get("site_price") or 0)
            percent = float(data.get("percent") or data.get("commission") or 0)
            final_price = base_price * (1 + (percent / 100)) if base_price > 0 else 0
            if final_price > 0:
                set_setting("saas_site_price_cache", str(final_price))
                return final_price
            print(f"[SAAS] Prix non disponible dans la réponse: {data}")
        print(f"[SAAS] Aucun endpoint prix n'a retourné de valeur exploitable")
    except Exception as e:
        print(f"[SAAS] Erreur récupération prix dashboard: {e}")
    cached = get_setting("saas_site_price_cache")
    try:
        return float(cached) if cached else None
    except Exception:
        return None

# Fonction helper pour récupérer le nombre de notifications non lues
def get_new_notifications_count():
    """Retourne le nombre de notifications admin non lues"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) 
        FROM notifications 
        WHERE user_id IS NULL AND is_read = 0
    """)
    count = c.fetchone()[0]
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
    
    print("Migration terminée ✅")
    
    # --- Activer l'auto-registration par défaut ---
    if not get_setting("enable_auto_registration"):
        set_setting("enable_auto_registration", "true")
        print("✅ Auto-registration activé par défaut")


def generate_invoice_pdf(order, items, total_price):
    file_path = f"temp_invoice_{order[0]}.pdf"
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # Titre
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, f"Facture #{order[0]}")

    # Infos client
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 90, f"Nom: {order[1]}")
    c.drawString(50, height - 110, f"Email: {order[2]}")
    c.drawString(50, height - 130, f"Adresse: {order[3]}")
    c.drawString(50, height - 150, f"Date: {order[5]}")

    # Table des articles
    y = height - 190
    c.drawString(50, y, "Articles:")
    y -= 20
    for item in items:
        c.drawString(60, y, f"{item[1]} x {item[4]} - {item[3]} €")
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
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True
    c = conn.cursor()

    session_id = request.cookies.get('cart_session')
    if not session_id:
        session_id = str(uuid.uuid4())
        c.execute(adapt_query("INSERT INTO carts (session_id) VALUES (?)"), (session_id,))
    else:
        c.execute(adapt_query("SELECT id FROM carts WHERE session_id=?"), (session_id,))
        if not c.fetchone():
            c.execute(adapt_query("INSERT INTO carts (session_id) VALUES (?)"), (session_id,))

    c.execute(adapt_query("SELECT id FROM carts WHERE session_id=?"), (session_id,))
    cart_id = c.fetchone()[0]

    user_id = session.get("user_id")
    if user_id:
        c.execute(adapt_query("UPDATE carts SET user_id=? WHERE id=?"), (user_id, cart_id))

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
    conn = get_db()
    c = conn.cursor()
    try:
        query = adapt_query("UPDATE users SET role='admin' WHERE email=?")
        c.execute(query, (email,))
        conn.commit()
        print(f"L'utilisateur {email} est maintenant administrateur")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        conn.close()

def merge_carts(user_id, session_id):
    conn = get_db()
    c = conn.cursor()

    # Récupère l'id du panier connecté
    c.execute(adapt_query("SELECT id FROM carts WHERE user_id=?"), (user_id,))
    user_cart = c.fetchone()
    c.execute(adapt_query("SELECT id FROM carts WHERE session_id=?"), (session_id,))
    session_cart = c.fetchone()

    if session_cart:
        session_cart_id = session_cart[0]

        if user_cart:
            user_cart_id = user_cart[0]
            # Fusion des articles
            c.execute(adapt_query("SELECT painting_id, quantity FROM cart_items WHERE cart_id=?"), (session_cart_id,))
            items = c.fetchall()
            for painting_id, qty in items:
                c.execute(adapt_query("SELECT quantity FROM cart_items WHERE cart_id=? AND painting_id=?"),
                          (user_cart_id, painting_id))
                row = c.fetchone()
                if row:
                    c.execute(adapt_query("UPDATE cart_items SET quantity=? WHERE cart_id=? AND painting_id=?"),
                              (row[0]+qty, user_cart_id, painting_id))
                else:
                    c.execute(adapt_query("INSERT INTO cart_items (cart_id, painting_id, quantity) VALUES (?, ?, ?)"),
                              (user_cart_id, painting_id, qty))
            # Supprime l’ancien panier de session
            c.execute(adapt_query("DELETE FROM cart_items WHERE cart_id=?"), (session_cart_id,))
            c.execute(adapt_query("DELETE FROM carts WHERE id=?"), (session_cart_id,))
        else:
            # Associe le panier de session à l'utilisateur
            c.execute(adapt_query("UPDATE carts SET user_id=? WHERE id=?"), (user_id, session_cart_id))

    conn.commit()
    conn.close()

# Initialisation de la base de données (une seule fonction suffit maintenant)
migrate_db()

# Définir l'administrateur
set_admin_user('coco.cayre@gmail.com')

# --------------------------------
# UTILITAIRES
# --------------------------------
def get_paintings():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, image, price, quantity, description FROM paintings")
    paintings = c.fetchall()
    conn.close()
    return paintings

def is_admin():
    """Vérifie si l'utilisateur connecté est admin"""
    user_id = session.get("user_id")
    if not user_id:
        return False
    
    conn = get_db()
    c = conn.cursor()
    c.execute(adapt_query("SELECT role FROM users WHERE id=?"), (user_id,))
    result = c.fetchone()
    conn.close()
    
    return result and result[0] == 'admin'

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
    conn = get_db()
    c = conn.cursor()

    # Sélection explicite pour latest_paintings
    c.execute("SELECT id, name, image, price, quantity, description FROM paintings ORDER BY id DESC LIMIT 4")
    latest_paintings = c.fetchall()

    # Sélection explicite pour all_paintings
    c.execute("SELECT id, name, image, price, quantity, description FROM paintings ORDER BY id DESC")
    all_paintings = c.fetchall()

    conn.close()
    return render_template("index.html", latest_paintings=latest_paintings, paintings=all_paintings)

@app.route('/about')
def about():
    # Récupérer toutes les peintures pour affichage dans la page à propos
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, image FROM paintings ORDER BY id DESC")
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
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)  # hachage du mot de passe

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute(adapt_query("INSERT INTO users (name, email, password) VALUES (?, ?, ?)"),
                      (name, email, hashed_password))
            conn.commit()
            conn.close()
            flash("Inscription réussie !")
            return redirect(url_for('login'))
        except Exception as e:
            conn.close()
            # IntegrityError pour email déjà utilisé
            if 'UNIQUE' in str(e) or 'unique' in str(e):
                flash("Cet email est déjà utilisé.")
            else:
                flash("Erreur lors de l'inscription.")
            return redirect(url_for('register'))

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        c = conn.cursor()

        # Vérifier utilisateur
        c.execute(adapt_query("SELECT id, password FROM users WHERE email=?"), (email,))
        user = c.fetchone()

        if not user or not check_password_hash(user[1], password):
            conn.close()
            flash("Email ou mot de passe incorrect")
            return redirect(url_for("login"))

        user_id = user[0]
        session["user_id"] = user_id

        # Récupérer panier invité actuel
        guest_session_id = request.cookies.get("cart_session")

        # Vérifier si l'utilisateur a déjà un panier
        c.execute(adapt_query("SELECT id, session_id FROM carts WHERE user_id=?"), (user_id,))
        user_cart = c.fetchone()

        if user_cart:
            # Panier utilisateur existant → récupérer session_id
            user_cart_session = user_cart[1]
        else:
            # Pas encore de panier user → en créer un
            user_cart_session = str(uuid.uuid4())
            c.execute(adapt_query("INSERT INTO carts (session_id, user_id) VALUES (?, ?)"),
                      (user_cart_session, user_id))
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
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM exhibitions ORDER BY date ASC")  # tri par date croissante
    expositions = c.fetchall()
    conn.close()

    today = date.today()

    # Cherche la prochaine exposition (la plus proche de la date d'aujourd'hui)
    next_expo = None
    other_expos = []

    for expo in expositions:
        expo_date = date.fromisoformat(expo[3])
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
    c.execute("""
        INSERT INTO custom_requests (client_name, client_email, client_phone, project_type, 
                                      description, budget, dimensions, deadline, reference_images, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'En attente')
    """, (client_name, client_email, client_phone, project_type, description, budget, dimensions, deadline, reference_images_json))
    request_id = c.lastrowid
    
    # Créer une notification pour l'admin
    c.execute(
        "INSERT INTO notifications (user_id, message, type, is_read, url) VALUES (?, ?, ?, ?, ?)",
        (None,  # user_id=None pour notifications admin
         f"Nouvelle demande de création sur mesure de {client_name}",
         "custom_request",
         0,
         f"/admin/custom-requests")
    )
    
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
    conn = get_db()
    c = conn.cursor()
    c.execute(adapt_query("SELECT * FROM exhibitions WHERE id=?"), (expo_id,))
    expo = c.fetchone()
    conn.close()
    if expo is None:
        return "Exposition introuvable", 404

    # Construire le chemin de l'image si elle existe
    image_url = None
    if expo[5]:
        # Vérifier si c'est déjà une URL complète
        if expo[5].startswith("http"):
            image_url = expo[5]
        else:
            image_url = url_for('static', filename='expo_images/' + expo[5])

    return render_template("expo_detail.html", expo=expo, image_url=image_url)

# --------------------------------
# ROUTES ADMIN DEMANDES SUR MESURE
# --------------------------------
@app.route("/admin/custom-requests")
@require_admin
def admin_custom_requests():
    status_filter = request.args.get('status')
    
    conn = get_db()
    c = conn.cursor()
    
    if status_filter:
        c.execute(adapt_query("SELECT * FROM custom_requests WHERE status=? ORDER BY created_at DESC"), (status_filter,))
    else:
        c.execute("SELECT * FROM custom_requests ORDER BY created_at DESC")
    
    requests_list = c.fetchall()
    
    # Compter par statut
    c.execute("SELECT COUNT(*) FROM custom_requests")
    total_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM custom_requests WHERE status='En attente'")
    pending_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM custom_requests WHERE status='En cours'")
    in_progress_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM custom_requests WHERE status='Acceptée'")
    accepted_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM custom_requests WHERE status='Refusée'")
    refused_count = c.fetchone()[0]
    
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
    new_status = request.form.get("status")
    
    conn = get_db()
    c = conn.cursor()
    c.execute(adapt_query("UPDATE custom_requests SET status=? WHERE id=?"), (new_status, request_id))
    conn.commit()
    conn.close()
    
    flash(f"Statut mis à jour : {new_status}", "success")
    return redirect(url_for("admin_custom_requests"))

@app.route("/admin/custom-requests/<int:request_id>/delete", methods=["POST"])
@require_admin
def delete_custom_request(request_id):
    conn = get_db()
    c = conn.cursor()
    
    # Récupérer les images avant suppression
    c.execute(adapt_query("SELECT reference_images FROM custom_requests WHERE id=?"), (request_id,))
    row = c.fetchone()
    if row and row[0]:
        import json
        images = json.loads(row[0])
        for image_path in images:
            full_path = os.path.join('static', image_path)
            if os.path.exists(full_path):
                os.remove(full_path)
    
    c.execute(adapt_query("DELETE FROM custom_requests WHERE id=?"), (request_id,))
    conn.commit()
    conn.close()
    
    flash("Demande supprimée avec succès", "success")
    return redirect(url_for("admin_custom_requests"))

# --------------------------------
# ROUTES EXPOSITIONS (ADMIN)
# --------------------------------
@app.route("/admin/exhibitions")
def admin_exhibitions():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM exhibitions ORDER BY create_date DESC")
    exhibitions = c.fetchall()
    conn.close()
    return render_template("admin/admin_exhibitions.html", 
                         exhibitions=exhibitions, 
                         new_notifications_count=get_new_notifications_count(),
                         active="exhibitions")


# Ajouter une exhibition
@app.route("/admin/exhibitions/add", methods=["GET", "POST"])
def add_exhibition():
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
            filename = secure_filename(file.filename)
            os.makedirs(app.config['EXPO_UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['EXPO_UPLOAD_FOLDER'], filename))
            image_filename = filename

        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO exhibitions (title, location, date, start_time, end_time, description, venue_details, organizer, entry_price, contact_info, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, location, date, start_time, end_time, description, venue_details, organizer, entry_price, contact_info, image_filename))
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
    conn = get_db()
    c = conn.cursor()
    c.execute(adapt_query("SELECT * FROM exhibitions WHERE id=?"), (exhibition_id,))
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

        image_filename = exhibition[5]  # Index de l'image dans la table
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config['EXPO_UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['EXPO_UPLOAD_FOLDER'], filename))
            image_filename = filename

        c.execute("""
            UPDATE exhibitions
            SET title=?, location=?, date=?, start_time=?, end_time=?, description=?, venue_details=?, organizer=?, entry_price=?, contact_info=?, image=?
            WHERE id=?
        """, (title, location, date, start_time, end_time, description, venue_details, organizer, entry_price, contact_info, image_filename, exhibition_id))
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
    conn = get_db()
    c = conn.cursor()
    # Supprimer l'image du dossier si elle existe
    c.execute(adapt_query("SELECT image FROM exhibitions WHERE id=?"), (exhibition_id,))
    image = c.fetchone()
    if image and image[0]:
        image_path = os.path.join(app.config['EXPO_UPLOAD_FOLDER'], image[0])
        if os.path.exists(image_path):
            os.remove(image_path)

    c.execute(adapt_query("DELETE FROM exhibitions WHERE id=?"), (exhibition_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_exhibitions"))

# ---------------------------------------------------------
# AJOUTER UN ARTICLE AU PANIER
# ---------------------------------------------------------
@app.route('/add_to_cart/<int:painting_id>', methods=['GET', 'POST'])
def add_to_cart(painting_id):
    cart_id, session_id = get_or_create_cart()
    conn = get_db()
    c = conn.cursor()
    
    # Récupérer la quantité depuis le formulaire POST ou défaut 1
    quantity_to_add = 1
    if request.method == 'POST':
        quantity_to_add = int(request.form.get('quantity', 1))

    # Vérifie si l'article existe déjà
    c.execute(adapt_query("SELECT quantity FROM cart_items WHERE cart_id=? AND painting_id=?"), (cart_id, painting_id))
    row = c.fetchone()
    if row:
        new_quantity = row[0] + quantity_to_add
        c.execute(adapt_query("UPDATE cart_items SET quantity=? WHERE cart_id=? AND painting_id=?"), (new_quantity, cart_id, painting_id))
    else:
        c.execute(adapt_query("INSERT INTO cart_items (cart_id, painting_id, quantity) VALUES (?, ?, ?)"), (cart_id, painting_id, quantity_to_add))

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
    cart_id, session_id = get_or_create_cart()
    conn = get_db()
    c = conn.cursor()

    c.execute(adapt_query("SELECT quantity FROM cart_items WHERE cart_id=? AND painting_id=?"), (cart_id, painting_id))
    row = c.fetchone()
    if row:
        new_qty = row[0] - 1
        if new_qty <= 0:
            c.execute(adapt_query("DELETE FROM cart_items WHERE cart_id=? AND painting_id=?"), (cart_id, painting_id))
        else:
            c.execute(adapt_query("UPDATE cart_items SET quantity=? WHERE cart_id=? AND painting_id=?"), (new_qty, cart_id, painting_id))

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
    cart_id, session_id = get_or_create_cart()
    conn = get_db()
    c = conn.cursor()

    c.execute(adapt_query("DELETE FROM cart_items WHERE cart_id=? AND painting_id=?"), (cart_id, painting_id))

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
    cart_id, session_id = get_or_create_cart()
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT paintings.id, paintings.name, paintings.image, paintings.price, cart_items.quantity, paintings.description
        FROM cart_items
        JOIN paintings ON cart_items.painting_id = paintings.id
        WHERE cart_items.cart_id=?
    ''', (cart_id,))
    items = c.fetchall()
    conn.close()

    total_price = sum(item[3] * item[4] for item in items)

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
    # Récupérer ou créer le panier
    cart_id, session_id = get_or_create_cart()

    conn = get_db()
    c = conn.cursor()

    # Récupérer les articles du panier
    c.execute('''
        SELECT paintings.id, paintings.name, paintings.image, paintings.price, cart_items.quantity, paintings.quantity
        FROM cart_items
        JOIN paintings ON cart_items.painting_id = paintings.id
        WHERE cart_items.cart_id=?
    ''', (cart_id,))
    items = c.fetchall()

    if not items:
        conn.close()
        return redirect(url_for('panier'))  # Panier vide

    total_price = sum(item[3] * item[4] for item in items)

    # Désactiver Stripe en mode preview
    if is_preview_request():
        conn.close()
        flash("Paiement désactivé en mode preview.")
        return redirect(url_for('home'))

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
        line_items = [{
            'price_data': {
                'currency': 'eur',
                'product_data': {'name': item[1]},
                'unit_amount': int(item[3] * 100),
            },
            'quantity': item[4],
        } for item in items]

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
    # Récupérer la commande en attente depuis la session
    order = session.pop("pending_order", None)
    if not order:
        return redirect(url_for('panier'))

    customer_name = order["customer_name"]
    email = order["email"]
    address = order.get("address") or ""  # Sécurisé
    total_price = order["total_price"]
    items = order["items"]

    with get_db() as conn:
        c = conn.cursor()

        # ----------------------------------------------------------
        # 1) Vérifier si l'utilisateur existe déjà
        # ----------------------------------------------------------
        c.execute(adapt_query("SELECT id FROM users WHERE email=?"), (email,))
        user = c.fetchone()

        if user:
            user_id = user[0]
        else:
            import secrets
            from werkzeug.security import generate_password_hash
            
            temp_password = secrets.token_hex(3)
            hashed_pw = generate_password_hash(temp_password)

            c.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (customer_name, email, hashed_pw)
            )
            conn.commit()
            user_id = c.lastrowid

            session["user_id"] = user_id
            session["user_email"] = email

        # ----------------------------------------------------------
        # 2) Créer la commande (AVEC address)
        # ----------------------------------------------------------
        c.execute(
            """
            INSERT INTO orders (customer_name, email, address, total_price, order_date, user_id)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """,
            (customer_name, email, address, total_price, user_id)
        )
        order_id = c.lastrowid

        # ----------------------------------------------------------
        # 3) Ajouter les items + mettre à jour les stocks
        # ----------------------------------------------------------
        for item in items:
            painting_id, name, image, price, qty, available_qty = item

            c.execute(
                "INSERT INTO order_items (order_id, painting_id, quantity, price) VALUES (?, ?, ?, ?)",
                (order_id, painting_id, qty, price)
            )

            c.execute(
                "UPDATE paintings SET quantity = quantity - ? WHERE id = ?",
                (qty, painting_id)
            )

        # ----------------------------------------------------------
        # 4) Vider le panier persistant
        # ----------------------------------------------------------
        cart_id, session_id = get_or_create_cart(conn=conn)
        c.execute(adapt_query("DELETE FROM cart_items WHERE cart_id=?"), (cart_id,))

        # ----------------------------------------------------------
        # 5) Notifications
        # ----------------------------------------------------------
        admin_order_url = url_for("admin_order_detail", order_id=order_id)
        user_order_url = url_for("order_status", order_id=order_id)

        # Admin
        c.execute(
            "INSERT INTO notifications (user_id, message, type, is_read, url) VALUES (?, ?, ?, ?, ?)",
            (None,
             f"Nouvelle commande #{order_id} passée par {customer_name} ({email})",
             "new_order",
             0,
             admin_order_url)
        )

        # User
        c.execute(
            "INSERT INTO notifications (user_id, message, type, is_read, url) VALUES (?, ?, ?, ?, ?)",
            (user_id,
             f"Votre commande #{order_id} a été confirmée !",
             "order_success",
             0,
             user_order_url)
        )

    # ----------------------------------------------------------
    # 6) Vider le panier en session
    # ----------------------------------------------------------
    session["cart"] = {}
    session["cart_count"] = 0

    # ----------------------------------------------------------
    # 7) Envoyer email
    # ----------------------------------------------------------
    send_order_email(
        customer_email=email,
        customer_name=customer_name,
        order_id=order_id,
        total_price=total_price,
        items=items
    )

    # ----------------------------------------------------------
    # 8) Afficher la page de succès
    # ----------------------------------------------------------
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
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                
                # Mettre à jour le setting avec le nouveau chemin
                set_setting("about_biography_image", f"Images/{unique_filename}")
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
        order_id = order[0]
        c.execute("""
            SELECT oi.painting_id, p.name, p.image, oi.price, oi.quantity
            FROM order_items oi
            JOIN paintings p ON oi.painting_id = p.id
            WHERE oi.order_id=?
        """, (order_id,))
        all_items[order_id] = c.fetchall()

    conn.close()

    return render_template("order.html", orders=orders_list, all_items=all_items)

@app.route('/admin/add', methods=['GET', 'POST'])
@require_admin
def add_painting_web():
    if request.method == 'POST':
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
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f'Images/{filename}'
            
            # Gestion des images additionnelles
            image_2 = None
            image_3 = None
            image_4 = None
            
            for i, field_name in enumerate(['image_2', 'image_3', 'image_4'], 2):
                if field_name in request.files:
                    file_extra = request.files[field_name]
                    if file_extra.filename and allowed_file(file_extra.filename):
                        filename_extra = secure_filename(file_extra.filename)
                        file_extra.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_extra))
                        if i == 2:
                            image_2 = f'Images/{filename_extra}'
                        elif i == 3:
                            image_3 = f'Images/{filename_extra}'
                        elif i == 4:
                            image_4 = f'Images/{filename_extra}'

            create_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = get_db()
            c = conn.cursor()
            c.execute(adapt_query("""
                INSERT INTO paintings (
                    name, image, price, quantity, description, create_date,
                    description_long, dimensions, technique, year, category, status,
                    image_2, image_3, image_4, weight, framed, certificate, unique_piece
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """), (
                name, image_path, price, quantity, description, create_date,
                description_long, dimensions, technique, year, category, status,
                image_2, image_3, image_4, weight, framed, certificate, unique_piece
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
    session_id = request.cookies.get("cart_session")
    user_id = session.get("user_id")

    conn = get_db()
    c = conn.cursor()

    # --- PANIER ---
    if user_id:
        c.execute(adapt_query("SELECT id FROM carts WHERE user_id=?"), (user_id,))
        row = c.fetchone()
        cart_id = row[0] if row else None
    else:
        if session_id:
            c.execute(adapt_query("SELECT id FROM carts WHERE session_id=?"), (session_id,))
            row = c.fetchone()
            cart_id = row[0] if row else None
        else:
            cart_id = None

    cart_items = []
    total_qty = 0
    if cart_id:
        c.execute("""
            SELECT ci.painting_id, p.name, p.image, p.price, ci.quantity
            FROM cart_items ci
            JOIN paintings p ON ci.painting_id = p.id
            WHERE ci.cart_id=?
        """, (cart_id,))
        cart_items = c.fetchall()
        total_qty = sum(item[4] for item in cart_items)

    # --- FAVORIS ---
    favorite_ids = []
    if user_id:
        c.execute(adapt_query("SELECT painting_id FROM favorites WHERE user_id=?"), (user_id,))
        favorite_ids = [row[0] for row in c.fetchall()]

    # --- NOTIFICATIONS ADMIN ---
    new_notifications_count = 0
    if is_admin():
        c.execute("SELECT COUNT(*) FROM notifications WHERE user_id IS NULL AND is_read=0")
        new_notifications_count = c.fetchone()[0]

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
        is_preview_host = is_preview_request() or bool(preview_data)
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

    with get_db() as conn:
        c = conn.cursor()
        # Récupérer toutes les notifications admin (user_id=NULL)
        c.execute("""
            SELECT id, message, url, is_read, created_at 
            FROM notifications 
            WHERE user_id IS NULL
            ORDER BY created_at DESC
        """)
        notifications = c.fetchall()

        # Compter les notifications non lues
        new_notifications_count = sum(1 for n in notifications if n[3] == 0)

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

    with get_db() as conn:
        c = conn.cursor()
        # Mettre la notification comme lue
        c.execute(adapt_query("UPDATE notifications SET is_read=1 WHERE id=?"), (notif_id,))
        # Récupérer l'URL pour redirection
        c.execute(adapt_query("SELECT url FROM notifications WHERE id=?"), (notif_id,))
        row = c.fetchone()
        redirect_url = row[0] if row and row[0] else url_for("admin_notifications")

    return redirect(redirect_url)


# --------------------------------
# ROUTE GALERIE
# --------------------------------
@app.route('/galerie')
def galerie():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, image, price, quantity FROM paintings ORDER BY display_order ASC, id DESC")
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
    
    data = request.get_json()
    painting_ids = data.get('order', [])
    
    if not painting_ids:
        return jsonify({'error': 'No order provided'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # Mettre à jour l'ordre d'affichage
    for index, painting_id in enumerate(painting_ids):
        c.execute(adapt_query(
            "UPDATE paintings SET display_order = ? WHERE id = ?"
        ), (index, painting_id))
    
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
    
    # Convertir en dict pour faciliter l'accès
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
                <div style="max-width:600px; margin:auto; background:white; border-radius:15px; padding:20px; box-shadow:0 5px 15px rgba(0,0,0,0.1);">
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
        order_id = order[0]
        c.execute("""
            SELECT oi.painting_id, p.name, p.image, oi.price, oi.quantity
            FROM order_items oi
            JOIN paintings p ON oi.painting_id = p.id
            WHERE oi.order_id=?
        """, (order_id,))
        items = c.fetchall()
        all_items[order_id] = items
        order_totals[order_id] = sum(item[3] * item[4] for item in items)

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
    formatted_orders = [
        {
            'id': order[0],
            'customer_name': order[1],
            'email': order[2],
            'address': order[3],
            'total': order[4],
            'date': order[5],
            'status': order[6]
        }
        for order in user_orders
    ]

    conn.close()

    return render_template(
        "profile.html",
        user={
            'id': user[0],
            'name': user[1],
            'email': user[2],
            'create_date': user[3]
        },
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

    total_price = sum(item[3] * item[4] for item in items)

    # PDF en mémoire
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    # --- Couleurs ---
    primary_color = colors.HexColor("#1E3A8A")
    grey_color = colors.HexColor("#333333")
    light_grey = colors.HexColor("#F5F5F5")

    # --- En-tête ---
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(50, height - 50, "JB Art")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 80, f"Facture - Commande #{order[0]}")

    c.setLineWidth(2)
    c.line(50, height - 95, width - 50, height - 95)

    # --- Infos client ---
    c.setFont("Helvetica", 12)
    c.setFillColor(grey_color)
    c.drawString(50, height - 120, f"Nom : {order[1]}")
    c.drawString(50, height - 140, f"Email : {order[2]}")
    c.drawString(50, height - 160, f"Adresse : {order[3]}")
    c.drawString(50, height - 180, f"Date : {order[5]}")
    c.drawString(50, height - 200, f"Statut : {order[6]}")

    # --- Tableau des articles ---
    y = height - 230
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(primary_color)

    # En-tête du tableau
    c.rect(50, y-4, 530, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.drawString(55, y, "Nom")
    c.drawRightString(420, y, "Prix (€)")
    c.drawRightString(490, y, "Quantité")
    c.drawRightString(580, y, "Sous-total (€)")

    y -= 20
    c.setFont("Helvetica", 12)
    for idx, item in enumerate(items):
        # Fond alterné
        if idx % 2 == 0:
            c.setFillColor(light_grey)
            c.rect(50, y-4, 530, 20, fill=1, stroke=0)
        c.setFillColor(grey_color)

        name = str(item[1])
        price = float(item[3])   # Prix unitaire
        qty = int(item[4])       # Quantité
        subtotal = price * qty

        c.drawString(55, y, name)
        c.drawRightString(490, y, f"{price:.2f}")   # Prix
        c.drawRightString(420, y, str(qty))         # Quantité
        c.drawRightString(580, y, f"{subtotal:.2f}")# Sous-total
        y -= 20

    # --- Total ---
    y -= 10
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(primary_color)
    c.rect(450, y-4, 130, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.drawRightString(580, y, f"Total : {total_price:.2f} €")

    # --- Footer ---
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(primary_color)
    c.drawString(50, 50, "Merci pour votre achat chez JB Art !")
    c.drawString(50, 35, "www.jbart.com")

    c.showPage()
    c.save()

    pdf_buffer.seek(0)
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

    conn = get_db()
    c = conn.cursor()

    try:
        c.execute(adapt_query("INSERT INTO favorites (user_id, painting_id) VALUES (?, ?)"), (user_id, painting_id))
        conn.commit()
        flash("Ajouté aux favoris !")
    except Exception as e:
        # IntegrityError pour doublon (favoris déjà existant)
        if 'UNIQUE' in str(e) or 'unique' in str(e):
            flash("Cette peinture est déjà dans vos favoris.")
        else:
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

    conn = get_db()
    c = conn.cursor()

    c.execute(adapt_query("DELETE FROM favorites WHERE user_id=? AND painting_id=?"), (user_id, painting_id))
    conn.commit()
    conn.close()

    flash("Retiré des favoris !")
    return redirect(request.referrer or url_for('home'))

@app.route('/is_favorite/<int:painting_id>')
def is_favorite(painting_id):
    user_id = session.get("user_id")
    if not user_id:
        return {'is_favorite': False}

    conn = get_db()
    c = conn.cursor()

    c.execute(adapt_query("SELECT 1 FROM favorites WHERE user_id=? AND painting_id=?"), (user_id, painting_id))
    result = c.fetchone()
    conn.close()

    return {'is_favorite': result is not None}

# --------------------------------
# ROUTES ADMINISTRATION
# --------------------------------
@app.route('/admin')
@require_admin
def admin_dashboard():
    """Tableau de bord administrateur"""
    conn = get_db()
    c = conn.cursor()
    
    # Statistiques
    c.execute("SELECT COUNT(*) FROM paintings")
    total_paintings = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]
    
    c.execute("SELECT SUM(total_price) FROM orders")
    total_revenue = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    # Dernières commandes
    c.execute("""
        SELECT id, customer_name, email, total_price, order_date, status 
        FROM orders 
        ORDER BY order_date DESC 
        LIMIT 5
    """)
    recent_orders = c.fetchall()
    
    # Peintures en rupture de stock
    c.execute("""
        SELECT id, name, price, quantity 
        FROM paintings 
        WHERE quantity <= 0 
        ORDER BY id DESC
    """)
    out_of_stock = c.fetchall()
    
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
    
    # Compter les notifications non lues
    c.execute("""
        SELECT COUNT(*) 
        FROM notifications 
        WHERE user_id IS NULL AND is_read = 0
    """)
    new_notifications_count = c.fetchone()[0]
    
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

    with get_db() as conn:
        c = conn.cursor()
        c.execute(adapt_query("DELETE FROM paintings WHERE id=?"), (painting_id,))
        conn.commit()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/painting/edit/<int:painting_id>', methods=['GET', 'POST'])
@require_admin
def edit_painting(painting_id):
    """Éditer une peinture"""
    conn = get_db()
    c = conn.cursor()
    
    # Récupérer la peinture avec tous les champs
    c.execute(adapt_query("""
        SELECT id, name, image, price, quantity, description, create_date,
               description_long, dimensions, technique, year, category, status,
               image_2, image_3, image_4, weight, framed, certificate, unique_piece
        FROM paintings WHERE id=?
    """), (painting_id,))
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
            c.execute(adapt_query("""
                UPDATE paintings SET 
                    name=?, price=?, quantity=?, image=?, description=?,
                    description_long=?, dimensions=?, technique=?, year=?, 
                    category=?, status=?, image_2=?, image_3=?, image_4=?,
                    weight=?, framed=?, certificate=?, unique_piece=?
                WHERE id=?
            """), (
                name, price, quantity, image_fields['image'], description,
                description_long, dimensions, technique, year,
                category, status, image_fields['image_2'], image_fields['image_3'], image_fields['image_4'],
                weight, framed, certificate, unique_piece,
                painting_id
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
    conn = get_db()
    c = conn.cursor()
    
    c.execute(adapt_query("SELECT image FROM paintings WHERE id=?"), (painting_id,))
    painting = c.fetchone()
    
    if painting:
        # Supprimer le fichier image
        image_path = os.path.join('static', painting[0])
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass
        
        # Supprimer de la BD
        c.execute(adapt_query("DELETE FROM paintings WHERE id=?"), (painting_id,))
        conn.commit()
        flash("Peinture supprimée avec succès !")
    else:
        flash("Peinture introuvable.")
    
    conn.close()
    return redirect(url_for('admin_paintings'))

@app.route('/admin/orders')
@require_admin
def admin_orders():
    """Gestion des commandes"""
    q = request.args.get('q', '').strip().lower()  # récupération du terme de recherche
    conn = get_db()
    c = conn.cursor()

    if q:
        # Requête avec recherche par ID ou nom client
        c.execute("""
            SELECT o.id, o.customer_name, o.email, o.address, o.total_price, o.order_date, o.status
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN paintings p ON oi.painting_id = p.id
            WHERE o.id LIKE ? 
               OR LOWER(o.customer_name) LIKE ?
               OR LOWER(p.name) LIKE ?
            GROUP BY o.id
            ORDER BY o.order_date DESC
        """, (f"%{q}%", f"%{q}%", f"%{q}%"))
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
        order_id = order[0]
        c.execute("""
            SELECT oi.painting_id, p.name, p.image, oi.price, oi.quantity
            FROM order_items oi
            JOIN paintings p ON oi.painting_id = p.id
            WHERE oi.order_id=?
        """, (order_id,))
        all_items[order_id] = c.fetchall()

    conn.close()
    return render_template('admin/admin_orders.html', 
                         orders=orders_list, 
                         all_items=all_items, 
                         new_notifications_count=get_new_notifications_count(),
                         active="orders")

@app.route("/order/<int:order_id>")
def order_status(order_id):
    conn = get_db()
    c = conn.cursor()

    # Récupérer la commande
    c.execute(adapt_query("SELECT id, customer_name, email, address, total_price, status FROM orders WHERE id=?"), (order_id,))
    order = c.fetchone()
    if not order:
        conn.close()
        abort(404)

    # Récupérer les articles avec info peinture
    c.execute("""
        SELECT oi.painting_id, p.name, p.image, oi.price, oi.quantity
        FROM order_items oi
        JOIN paintings p ON oi.painting_id = p.id
        WHERE oi.order_id=?
    """, (order_id,))
    items = c.fetchall()

    conn.close()

    total_price = order[4]

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
    valid_statuses = ['En cours', 'Confirmée', 'Expédiée', 'Livrée', 'Annulée']
    
    if status not in valid_statuses:
        flash("Statut invalide.")
        return redirect(url_for('admin_orders'))
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute(adapt_query("UPDATE orders SET status=? WHERE id=?"), (status, order_id))
    conn.commit()
    conn.close()
    
    flash(f"Commande #{order_id} mise à jour : {status}")
    return redirect(url_for('admin_orders'))


@app.route("/admin/orders/<int:order_id>")
def admin_order_detail(order_id):
    if not is_admin():
        return redirect(url_for("index"))

    conn = get_db()
    c = conn.cursor()

    # Récupérer la commande
    c.execute(adapt_query("SELECT id, customer_name, email, address, total_price, order_date, status FROM orders WHERE id=?"), (order_id,))
    order = c.fetchone()
    if not order:
        conn.close()
        return "Commande introuvable", 404

    # Récupérer les articles de la commande
    c.execute("""
        SELECT oi.painting_id, p.name, p.image, oi.price, oi.quantity
        FROM order_items oi
        JOIN paintings p ON oi.painting_id = p.id
        WHERE oi.order_id=?
    """, (order_id,))
    items = c.fetchall()
    conn.close()

    return render_template("admin/admin_order_detail.html", 
                         order=order, 
                         items=items, 
                         new_notifications_count=get_new_notifications_count())


@app.route('/admin/users')
@require_admin
def admin_users():
    """Gestion des utilisateurs avec recherche et filtre par rôle"""
    q = request.args.get('q', '').strip().lower()
    role = request.args.get('role', '').strip().lower()
    
    conn = get_db()
    c = conn.cursor()

    query = "SELECT id, name, email, role, create_date FROM users"
    conditions = []
    params = []

    # Recherche texte
    if q:
        conditions.append("""(
            CAST(id AS TEXT) LIKE ?
            OR LOWER(name) LIKE ?
            OR LOWER(email) LIKE ?
            OR LOWER(role) LIKE ?
            OR LOWER(create_date) LIKE ?
        )""")
        params.extend([f"%{q}%"] * 5)

    # Filtre rôle
    if role:
        conditions.append("LOWER(role) = ?")
        params.append(role)

    # Construire la requête finale
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC"

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
    valid_roles = ['user', 'admin', 'partenaire']
    
    role = request.form.get('role')
    if role not in valid_roles:
        flash("Rôle invalide.")
        return redirect(url_for('admin_users'))
    
    conn = get_db()
    c = conn.cursor()
    
    # Ne pas laisser supprimer l'admin principal
    c.execute(adapt_query("SELECT email FROM users WHERE id=?"), (user_id,))
    user = c.fetchone()
    
    if user and user[0] == 'coco.cayre@gmail.com' and role != 'admin':
        flash("Impossible de retirer le rôle admin à l'administrateur principal.")
        conn.close()
        return redirect(url_for('admin_users'))
    
    c.execute(adapt_query("UPDATE users SET role=? WHERE id=?"), (role, user_id))
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
    emails = [row[0] for row in c.fetchall()]
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
        image_path = os.path.join("static", item[2])
        items_html += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 15px 10px;">
                <img src="cid:{cid}" alt="{item[1]}" style="
                    width: 80px;
                    height: 80px;
                    object-fit: cover;
                    border-radius: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                ">
            </td>
            <td style="padding: 15px 10px;">
                <strong style="color: #1a1a1a; font-size: 15px;">{item[1]}</strong><br>
                <span style="color: #666; font-size: 14px;">Quantité : {item[4]}</span>
            </td>
            <td style="padding: 15px 10px; text-align: right;">
                <strong style="color: {color_primary}; font-size: 16px;">{item[3]} €</strong>
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

# --------------------------------
# KEYS
# --------------------------------
stripe.api_key = get_setting("stripe_secret_key")

# --------------------------------
# ROUTE CSS DYNAMIQUE (COULEURS)
# --------------------------------
def get_luminance(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255

@app.route('/dynamic-colors.css')
def dynamic_colors():
    primary_color = get_setting("primary_color") or "#1E3A8A"
    secondary_color = get_setting("secondary_color") or "#3B65C4"
    accent_color = get_setting("accent_color") or "#FF7F50"
    button_text_color = get_setting("button_text_color") or "#FFFFFF"
    content_text_color = get_setting("content_text_color") or "#000000"
    button_hover_color = get_setting("button_hover_color") or "#9C27B0"

    css = f"""
:root {{
    --primary-color: {primary_color};
    --secondary-color: {secondary_color};
    --accent-color: {accent_color};
    --button-text-color: {button_text_color};
    --content-text-color: {content_text_color};
    --button-hover-color: {button_hover_color};
}}

/* GLOBAL TEXT COLOR - CONTENT BY DEFAULT */
* {{
    color: var(--content-text-color) !important;
}}

html, body {{
    color: var(--content-text-color) !important;
}}

/* NAVIGATION */
nav {{
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
}}

nav .logo,
nav a {{
    color: var(--button-text-color) !important;
}}

nav a:hover {{
    background: rgba(255, 255, 255, 0.2) !important;
}}

/* RESPONSIVE NAV MENU */
@media (max-width: 768px) {{
    nav ul {{
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
    }}
}}

/* HERO */
.hero-overlay {{
    background: linear-gradient(to bottom, rgba(0,0,50,0.2), rgba({int(primary_color[1:3], 16)},{int(primary_color[3:5], 16)},{int(primary_color[5:7], 16)},0.6)) !important;
}}

/* SECTIONS & TEXT */
.section h2,
h1, h2, h3 {{
    color: var(--content-text-color) !important;
}}

a {{
    color: var(--content-text-color) !important;
}}

a:hover {{
    color: var(--primary-color) !important;
}}

body, p, span, li, td {{
    color: var(--content-text-color) !important;
}}

/* PROFILE HEADER */
.profile-header {{
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
    color: var(--button-text-color) !important;
}}

.profile-header h1,
.profile-email,
.profile-meta {{
    color: var(--button-text-color) !important;
}}

.action-btn {{
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
    color: var(--button-text-color) !important;
}}

.action-btn:hover {{
    background: var(--button-hover-color) !important;
}}

/* PROFILE BUY BUTTON */
.buy-btn {{
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
    color: var(--button-text-color) !important;
}}

.buy-btn:hover {{
    background: var(--button-hover-color) !important;
}}

/* ORDERS TABLE */
.orders-table thead {{
    background: var(--primary-color) !important;
}}

.orders-table th {{
    color: var(--button-text-color) !important;
}}

/* MEGA MENU (fond blanc, toujours texte noir) */
.user-menu-links a,
.user-menu-section-title,
.cart-preview,
.cart-item-details p {{
    color: #000000 !important;
}}

.user-menu-links a:hover {{
    background: var(--button-hover-color) !important;
    color: white !important;
    border-radius: 6px !important;
    transform: translateX(4px) !important;
}}

.cart-item:hover {{
    background: rgba(156, 39, 176, 0.1) !important;
    border-color: var(--button-hover-color) !important;
    box-shadow: 0 2px 8px rgba(156, 39, 176, 0.2) !important;
}}

.mega-menu-cart-btn {{
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
    color: var(--button-text-color) !important;
}}

.mega-menu-cart-btn:hover {{
    background: var(--button-hover-color) !important;
    color: var(--button-text-color) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}}

/* PROFILE BUY BUTTON */
.buy-btn {{
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
    color: var(--button-text-color) !important;
}}

.buy-btn:hover {{
    background: var(--button-hover-color) !important;
}}

/* PROFILE BUY BUTTON */
.buy-btn {{
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
    color: var(--button-text-color) !important;
}}

.buy-btn:hover {{
    background: var(--button-hover-color) !important;
}}

/* ORDERS TABLE */
.orders-table thead {{
    background: var(--primary-color) !important;
}}

.orders-table th {{
    color: var(--button-text-color) !important;
}}

/* BUTTONS & BADGES */
.latest-artwork .badge {{
    background: linear-gradient(90deg, var(--accent-color), #FF4500) !important;
    color: var(--button-text-color) !important;
}}

button,
.btn-primary,
.latest-artwork button,
.add-painting-form button,
.validate-btn,
.qty-btn,
[class*="btn"] {{
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
    color: var(--button-text-color) !important;
    border: none !important;
}}

button:hover,
.btn-primary:hover,
.latest-artwork button:hover,
.add-painting-form button:hover,
.validate-btn:hover,
.qty-btn:hover,
[class*="btn"]:hover {{
    background: var(--button-hover-color) !important;
    color: var(--button-text-color) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}}

/* FORMS */
input:focus,
textarea:focus,
select:focus {{
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.1) !important;
    outline: none !important;
}}

input {{
    border-color: var(--primary-color) !important;
}}

/* FOOTER */
footer {{
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color)) !important;
}}

footer,
footer p,
footer a,
.footer-links ul li a {{
    color: var(--button-text-color) !important;
}}

footer a:hover {{
    color: var(--accent-color) !important;
}}

/* LINKS IN FOOTER */
.footer-links ul li a:hover {{
    color: var(--accent-color) !important;
}}

/* BORDERS & ACCENTS */
.form-group input,
.form-group textarea {{
    border-color: var(--primary-color) !important;
}}

.form-group input:focus,
.form-group textarea:focus {{
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 3px rgba(30, 58, 138, 0.1) !important;
}}

/* ADMIN HEADER */
.admin-header {{
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
    color: var(--button-text-color) !important;
}}

.admin-header h1 {{
    color: var(--button-text-color) !important;
}}

/* ADMIN ELEMENTS */
.admin-form {{
    border-left: 4px solid var(--primary-color) !important;
}}

.admin-nav {{
    background: transparent !important;
}}

.admin-nav .nav-btn {{
    background: rgba(255, 255, 255, 0.2) !important;
    color: var(--button-text-color) !important;
    border: none !important;
    padding: 10px 16px !important;
    border-radius: 6px !important;
    text-decoration: none !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
}}

.admin-nav .nav-btn:hover {{
    background: var(--button-hover-color) !important;
    color: var(--button-text-color) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}}

.status-badge {{
    background: var(--primary-color) !important;
    color: var(--button-text-color) !important;
}}

/* ALERTS */
.alert-success {{
    border-left: 4px solid var(--primary-color) !important;
}}

/* GALLERY & CARDS */
.latest-artwork {{
    border: 2px solid var(--primary-color) !important;
}}

.product-card {{
    border: 2px solid var(--primary-color) !important;
}}

.cart-item {{
    border-left: 4px solid var(--primary-color) !important;
}}

/* ACCENT ELEMENTS */
.badge {{
    background: var(--accent-color) !important;
    color: var(--button-text-color) !important;
}}

.highlight {{
    color: var(--accent-color) !important;
}}

/* FOCUS STATES */
:focus {{
    outline-color: var(--primary-color) !important;
}}

::placeholder {{
    color: var(--primary-color) !important;
    opacity: 0.6;
}}

/* TABS & ACTIVE STATES */
.nav-btn.active {{
    background: var(--accent-color) !important;
    color: var(--button-text-color) !important;
}}

.tab-active {{
    border-bottom-color: var(--primary-color) !important;
    color: var(--primary-color) !important;
}}

/* HOVER EFFECTS */
.latest-artwork:hover {{
    box-shadow: 0 10px 25px rgba({int(primary_color[1:3], 16)},{int(primary_color[3:5], 16)},{int(primary_color[5:7], 16)},0.2) !important;
    border-color: var(--secondary-color) !important;
}}

/* TOTAL PRICE & IMPORTANT TEXT */
.total-price {{
    color: var(--primary-color) !important;
    font-weight: 700 !important;
}}

/* SECTION BACKGROUNDS */
.admin-section {{
    background: linear-gradient(135deg, rgba({int(primary_color[1:3], 16)},{int(primary_color[3:5], 16)},{int(primary_color[5:7], 16)},0.02), rgba({int(secondary_color[1:3], 16)},{int(secondary_color[3:5], 16)},{int(secondary_color[5:7], 16)},0.02)) !important;
}}

.stats-grid .stat-card {{
    border-left: 4px solid var(--primary-color) !important;
}}

/* CARDS & CONTAINERS WITH TEXT */
.stat-card,
.painting-card,
.product-card,
.artwork-card,
.form-group,
.modal,
.modal-content,
.panel,
.box,
.card {{
    background: white !important;
}}

.stat-card h3,
.stat-card p,
.stat-card .stat-number,
.stat-card .stat-info,
.painting-card h3,
.painting-card p,
.product-card h3,
.product-card p,
.product-card .info,
.artwork-card h3,
.artwork-card p,
.form-group label,
.modal h1,
.modal h2,
.modal h3,
.modal p,
.panel h3,
.panel p,
.box p,
.card p,
.card h3 {{
    color: var(--content-text-color) !important;
}}

/* INPUTS & TEXTAREAS */
input,
textarea,
select {{
    background: white !important;
    color: var(--content-text-color) !important;
}}

input::placeholder,
textarea::placeholder,
select {{
    color: var(--content-text-color) !important;
    opacity: 0.6;
}}

/* SECTIONS */
.section,
.section-content,
.page-section,
.content-section {{
    background: transparent !important;
}}

.section p,
.section-content p,
.page-section p,
.content-section p {{
    color: var(--content-text-color) !important;
}}

/* LISTS & ITEMS */
ul, ol {{
    color: var(--content-text-color) !important;
}}

ul li,
ol li,
li {{
    color: var(--content-text-color) !important;
}}

/* TABLES */
table,
th,
td {{
    color: var(--content-text-color) !important;
    border-color: var(--primary-color) !important;
}}

th {{
    background: rgba(30, 58, 138, 0.1) !important;
}}

/* ALERT & SUCCESS MESSAGES */
.alert,
.alert-success,
.alert-error,
.alert-warning,
.alert-info {{
    color: var(--content-text-color) !important;
}}

/* ADMIN & FORMS */
.admin-form,
.admin-section,
.form-section,
.form-row,
.form-container,
.table-container,
.data-table,
.admin-table {{
    background: white !important;
}}

.admin-form h3,
.admin-form p,
.admin-form label,
.admin-section h3,
.admin-section p,
.form-section h3,
.form-section p,
.table-container h3,
.data-table td,
.admin-table td,
.admin-table th {{
    color: var(--content-text-color) !important;
}}

/* GENERAL TEXT ELEMENTS */
dt, dd,
blockquote,
.text-content,
.description,
.metadata,
.info-box,
.note {{
    color: var(--content-text-color) !important;
}}

/* GRID ITEMS */
.grid-item,
.item,
.row,
.col {{
    color: var(--content-text-color) !important;
}}

/* RESPONSIVE & TRANSITIONS */
button,
a,
input,
.latest-artwork,
.product-card,
.btn-primary {{
    transition: color 0.3s ease, background-color 0.3s ease, border-color 0.3s ease, transform 0.2s ease, box-shadow 0.2s ease !important;
}}

/* UNIFORM HOVER EFFECT FOR ALL INTERACTIVE ELEMENTS */
a[href]:not(.user-menu-section-title):hover {{
    opacity: 0.8 !important;
}}

input[type="button"]:hover,
input[type="submit"]:hover,
input[type="reset"]:hover {{
    background: var(--button-hover-color) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}}

.latest-artwork:hover,
.product-card:hover {{
    transform: translateY(-4px) !important;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15) !important;
}}
"""
    response = make_response(css)
    response.headers["Content-Type"] = "text/css"
    return response


# ================================
# API EXPORT DE DONNÉES
# ================================

def require_api_key(f):
    """Décorateur pour vérifier la clé API"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API key manquante"}), 401
        
        # Vérifier la clé API dans les settings
        stored_key = get_setting("export_api_key")
        if not stored_key:
            # Générer une clé si elle n'existe pas
            stored_key = secrets.token_urlsafe(32)
            set_setting("export_api_key", stored_key)
            print(f"🔑 Nouvelle clé API générée: {stored_key}")
        
        if api_key != stored_key:
            return jsonify({"error": "Clé API invalide"}), 403
        
        return f(*args, **kwargs)
    return decorated_function


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
                if rows:
                    columns = [description[0] for description in cur.description]
                    data[table_name] = [dict(zip(columns, row)) for row in rows]
                else:
                    data[table_name] = []
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


@app.route('/api/export/paintings', methods=['GET'])
@require_api_key
def api_export_paintings():
    """Exporte uniquement les peintures"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(adapt_query("SELECT * FROM paintings ORDER BY display_order, id"))
        rows = cur.fetchall()
        
        columns = [description[0] for description in cur.description]
        paintings = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(paintings),
            "data": paintings
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/orders', methods=['GET'])
@require_api_key
def api_export_orders():
    """Exporte les commandes avec leurs items"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Récupérer toutes les commandes
        cur.execute(adapt_query("SELECT * FROM orders ORDER BY order_date DESC"))
        orders_rows = cur.fetchall()
        columns = [description[0] for description in cur.description]
        orders = [dict(zip(columns, row)) for row in orders_rows]
        
        # Pour chaque commande, récupérer les items
        for order in orders:
            cur.execute(adapt_query("""
                SELECT oi.*, p.name, p.image 
                FROM order_items oi
                LEFT JOIN paintings p ON oi.painting_id = p.id
                WHERE oi.order_id = ?
            """), (order['id'],))
            items_rows = cur.fetchall()
            items_columns = [description[0] for description in cur.description]
            order['items'] = [dict(zip(items_columns, row)) for row in items_rows]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(orders),
            "data": orders
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/users', methods=['GET'])
@require_api_key
def api_export_users():
    """Exporte les utilisateurs (sans mots de passe)"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(adapt_query("SELECT id, name, email, role, create_date, phone, address, city, postal_code, country, birth_date, accepts_marketing FROM users"))
        rows = cur.fetchall()
        
        columns = [description[0] for description in cur.description]
        users = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(users),
            "data": users
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/exhibitions', methods=['GET'])
@require_api_key
def api_export_exhibitions():
    """Exporte les expositions"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(adapt_query("SELECT * FROM exhibitions ORDER BY date DESC"))
        rows = cur.fetchall()
        
        columns = [description[0] for description in cur.description]
        exhibitions = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(exhibitions),
            "data": exhibitions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/custom-requests', methods=['GET'])
@require_api_key
def api_export_custom_requests():
    """Exporte les demandes personnalisées"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(adapt_query("SELECT * FROM custom_requests ORDER BY created_at DESC"))
        rows = cur.fetchall()
        
        columns = [description[0] for description in cur.description]
        requests_data = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(requests_data),
            "data": requests_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/settings', methods=['GET'])
@require_api_key
def api_export_settings():
    """Exporte les paramètres (sauf clés sensibles)"""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(adapt_query("SELECT * FROM settings"))
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
    try:
        conn = get_db()
        cur = conn.cursor()
        
        stats = {}
        
        # Compter les enregistrements dans chaque table
        for table_name in TABLES.keys():
            try:
                cur.execute(adapt_query(f"SELECT COUNT(*) FROM {table_name}"))
                count = cur.fetchone()[0]
                stats[f"{table_name}_count"] = count
            except:
                stats[f"{table_name}_count"] = 0
        
        # Statistiques supplémentaires
        try:
            cur.execute(adapt_query("SELECT SUM(total_price) FROM orders"))
            total_revenue = cur.fetchone()[0] or 0
            stats['total_revenue'] = float(total_revenue)
        except:
            stats['total_revenue'] = 0
        
        try:
            cur.execute(adapt_query("SELECT COUNT(*) FROM orders WHERE status = 'Livrée'"))
            stats['delivered_orders'] = cur.fetchone()[0] or 0
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


@app.route('/api/export/settings/<key>', methods=['PUT'])
@require_api_key
def update_setting_api(key):
    """Modifier un paramètre spécifique via l'API"""
    try:
        data = request.get_json()
        new_value = data.get('value')
        
        if new_value is None:
            return jsonify({'success': False, 'error': 'Valeur manquante'}), 400
        
        # Mettre à jour dans la base de données
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(adapt_query('UPDATE settings SET value = ? WHERE key = ?'), (new_value, key))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Paramètre non trouvé'}), 404
        
        conn.close()
        return jsonify({'success': True, 'message': f'Paramètre {key} mis à jour'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
    Récupère ou génère la clé API pour l'export
    Accessible uniquement aux administrateurs connectés
    """
    api_key = get_setting("export_api_key")
    if not api_key:
        api_key = secrets.token_urlsafe(32)
        set_setting("export_api_key", api_key)
    
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
# FIN API EXPORT
# ================================

# ================================
# SYSTÈME AUTO-REGISTRATION AU DASHBOARD CENTRAL
# ================================

def auto_generate_api_key():
    """Génère automatiquement une clé API si elle n'existe pas"""
    api_key = get_setting("export_api_key")
    if not api_key:
        api_key = secrets.token_urlsafe(32)
        set_setting("export_api_key", api_key)
        print(f"✅ Clé API générée automatiquement: {api_key[:10]}...")
    return api_key

def register_site_to_dashboard():
    """Enregistre automatiquement ce site sur le dashboard central"""
    import requests
    
    # Vérifier si déjà enregistré
    if get_setting("dashboard_registered") == "true":
        print("[AUTO-REG] Site déjà enregistré sur le dashboard")
        return
    
    # Vérifier si l'enregistrement est activé (avec override par variable d'environnement)
    env_override = (os.getenv("ENABLE_AUTO_REGISTRATION", "").strip().lower() in ("true", "1", "yes"))
    enabled_setting = get_setting("enable_auto_registration")
    is_enabled = env_override or (enabled_setting == "true")
    if not is_enabled:
        print("[AUTO-REG] Auto-registration désactivé. Génération de l'API key uniquement.")
        auto_generate_api_key()
        return
    
    try:
        # Générer l'API key
        api_key = auto_generate_api_key()
        
        # Récupérer les infos du site
        site_name = get_setting("site_name") or "Site Artiste"
        
        # Détecter l'URL du site (compatible Render)
        site_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("SITE_URL")
        if not site_url:
            render_service = os.getenv("RENDER_SERVICE_NAME")
            if render_service:
                site_url = f"https://{render_service}.onrender.com"
            else:
                print("[AUTO-REG] ⚠️ Impossible de déterminer l'URL - skip registration")
                return
        
        site_url = site_url.rstrip('/')
        
        # Données à envoyer (minimales, alignées avec un schéma classique)
        # Certains dashboards attendent des clés génériques: name, url, api_key
        # On évite tout champ non indispensable pour contourner des migrations manquantes côté dashboard.
        data = {
            "name": site_name,
            "url": site_url,
            "api_key": api_key
        }
        
        # URL du dashboard central
        dashboard_url = "https://mydashboard-v39e.onrender.com/api/sites/register"
        
        print(f"[AUTO-REG] 📤 Enregistrement sur le dashboard central...")
        print(f"[AUTO-REG]    Nom: {site_name}")
        print(f"[AUTO-REG]    URL: {site_url}")
        print(f"[AUTO-REG]    Dashboard: {dashboard_url}")
        
        # Envoyer les données
        response = requests.post(dashboard_url, json=data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            site_id = result.get("site_id")
            set_setting("dashboard_registered", "true")
            set_setting("dashboard_id", str(site_id))
            print(f"[AUTO-REG] ✅ {result.get('message', 'Site enregistré')} - Site ID: {site_id}")
        elif response.status_code == 404:
            print(f"[AUTO-REG] ⚠️ Erreur 404: L'endpoint /api/sites/register n'existe pas encore")
            print(f"[AUTO-REG]    L'API key est générée localement et reste fonctionnelle.")
        else:
            print(f"[AUTO-REG] ⚠️ Erreur {response.status_code}: {response.text}")
    
    except requests.exceptions.Timeout:
        print(f"[AUTO-REG] ⚠️ Timeout: Le dashboard ne répond pas")
        print(f"[AUTO-REG]    L'API key est générée localement et reste fonctionnelle.")
    except Exception as e:
        print(f"[AUTO-REG] ⚠️ Erreur: {e}")
        print(f"[AUTO-REG]    L'API key est générée localement et reste fonctionnelle.")
        # S'assurer que l'API key est générée même en cas d'erreur
        auto_generate_api_key()

@app.route('/api/sync-dashboard', methods=['POST'])
def sync_dashboard():
    """Endpoint manuel pour forcer la synchronisation avec le dashboard"""
    try:
        # Réinitialiser le flag
        set_setting("dashboard_registered", "false")
        
        # Relancer l'enregistrement
        register_site_to_dashboard()
        
        return jsonify({
            'success': True,
            'message': 'Sync triggered'
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
    if is_preview_request():
        flash("Stripe est désactivé en mode preview.")
        return redirect(url_for('home'))

    price = fetch_dashboard_site_price()
    if not price or price <= 0:
        flash("Prix indisponible pour le lancement.")
        return redirect(url_for('home'))

    stripe_secret = get_setting("stripe_secret_key")
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
                'site_id': get_setting('dashboard_id') or '',
                'user_id': session.get('user_id') or '',
                'context': 'saas_launch'
            }
        )
        return redirect(session_obj.url, code=303)
    except Exception as e:
        print(f"[SAAS] Erreur création session Stripe: {e}")
        flash("Impossible de lancer la session de paiement pour le moment.")
        return redirect(url_for('home'))


@app.route('/saas/launch/success')
def saas_launch_success():
    flash("Merci ! Paiement reçu, nous lançons votre site.")
    return redirect(url_for('home'))


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
