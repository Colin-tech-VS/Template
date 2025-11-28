# --------------------------------
# IMPORTS
# --------------------------------
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, send_file, abort
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime, date
import stripe
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import tempfile
from io import BytesIO
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from flask_mail import Message, Mail
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
import secrets
from openpyxl import Workbook
import tempfile



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

DB_PATH = 'paintings.db'

# Dossiers de stockage
app.config['UPLOAD_FOLDER'] = 'static/Images'        # pour les peintures
app.config['EXPO_UPLOAD_FOLDER'] = 'static/expo_images'  # pour les exhibitions

# Extensions autorisées (communes aux deux)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Vérification d'extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    return sqlite3.connect(DB_PATH)


def get_order_by_id(order_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    conn.close()
    return order

def get_order_items(order_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
    items = cursor.fetchall()
    conn.close()
    return items
TABLES = {
    "paintings": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "name": "TEXT NOT NULL",
        "image": "TEXT NOT NULL",
        "price": "REAL NOT NULL DEFAULT 0",
        "quantity": "INTEGER NOT NULL DEFAULT 0",
        "create_date": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "description": "TEXT"
    },
    "orders": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "customer_name": "TEXT NOT NULL",
        "email": "TEXT NOT NULL",
        "address": "TEXT NOT NULL",
        "total_price": "REAL NOT NULL",
        "order_date": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "status": "TEXT NOT NULL DEFAULT 'En cours'"
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
        "description": "TEXT",
        "image": "TEXT",
        "create_date": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
    },
    # Nouvelle table settings pour stocker toutes les clés API et configs
    "settings": {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "key": "TEXT UNIQUE NOT NULL",
        "value": "TEXT NOT NULL"
    }
}

# --- Décorateur admin ---
def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Exemple : vérifier si session['role'] == 'admin'
        if 'role' not in session or session['role'] != 'admin':
            flash("Accès refusé")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Fonction utilitaire pour récupérer une clé depuis settings
def get_setting(key):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else None

stripe_key = get_setting("stripe_secret_key")
print("Clé Stripe actuelle :", stripe_key)

# Vérifier les valeurs SMTP
smtp_server = get_setting("smtp_server") or "smtp.gmail.com"
smtp_port = int(get_setting("smtp_port") or 587)
smtp_user = get_setting("email_sender") or "coco.cayre@gmail.com"
smtp_password = get_setting("smtp_password") or "motdepassepardefaut"

print("SMTP_SERVER :", smtp_server)
print("SMTP_PORT   :", smtp_port)
print("SMTP_USER   :", smtp_user)
print("SMTP_PASSWORD :", smtp_password)

google_places_key = get_setting("google_places_key") or "CLE_PAR_DEFAUT"
print("Google Places Key utilisée :", google_places_key)  # <-- vérification dans la console


# Fonction utilitaire pour mettre à jour ou créer une clé
def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    conn.commit()
    conn.close()

def create_table_if_not_exists(table_name, columns):
    """Crée la table si elle n'existe pas"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    col_defs = ", ".join([f"{name} {ctype}" for name, ctype in columns.items()])
    c.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})")
    conn.commit()
    conn.close()

def add_column_if_not_exists(table_name, column_name, column_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Vérifier les colonnes existantes
    c.execute(f"PRAGMA table_info({table_name})")
    existing_cols = [col[1] for col in c.fetchall()]
    
    if column_name not in existing_cols:
        # Ajouter directement la colonne telle quelle
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        c.execute(sql)
        print(f"Colonne '{column_name}' ajoutée à '{table_name}'")
    
    conn.commit()
    conn.close()

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
    """Migration des colonnes manquantes pour orders"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in c.fetchall()]
    if 'status' not in columns:
        c.execute("ALTER TABLE orders ADD COLUMN status TEXT NOT NULL DEFAULT 'En cours'")
    conn.commit()
    conn.close()

def get_or_create_cart(conn=None):
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        close_conn = True
    c = conn.cursor()

    session_id = request.cookies.get('cart_session')
    if not session_id:
        session_id = str(uuid.uuid4())
        c.execute("INSERT INTO carts (session_id) VALUES (?)", (session_id,))
    else:
        c.execute("SELECT id FROM carts WHERE session_id=?", (session_id,))
        if not c.fetchone():
            c.execute("INSERT INTO carts (session_id) VALUES (?)", (session_id,))

    c.execute("SELECT id FROM carts WHERE session_id=?", (session_id,))
    cart_id = c.fetchone()[0]

    user_id = session.get("user_id")
    if user_id:
        c.execute("UPDATE carts SET user_id=? WHERE id=?", (user_id, cart_id))

    if close_conn:
        conn.close()

    return cart_id, session_id


def init_users_table():
    """Crée la table users si elle n'existe pas"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            create_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def migrate_orders_user():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in c.fetchall()]
    if 'user_id' not in columns:
        c.execute("ALTER TABLE orders ADD COLUMN user_id INTEGER")
    conn.commit()
    conn.close()

def migrate_users_role():
    """Ajoute la colonne role à la table users si elle n'existe pas"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if 'role' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        conn.commit()
    conn.close()

def set_admin_user(email):
    """Définit un utilisateur comme administrateur"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET role='admin' WHERE email=?", (email,))
        conn.commit()
        print(f"L'utilisateur {email} est maintenant administrateur")
    except Exception as e:
        print(f"Erreur : {e}")
    finally:
        conn.close()

def init_favorites_table():
    """Crée la table favorites si elle n'existe pas"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            painting_id INTEGER NOT NULL,
            created_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(painting_id) REFERENCES paintings(id),
            UNIQUE(user_id, painting_id)
        )
    ''')
    conn.commit()
    conn.close()

def merge_carts(user_id, session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Récupère l'id du panier connecté
    c.execute("SELECT id FROM carts WHERE user_id=?", (user_id,))
    user_cart = c.fetchone()
    c.execute("SELECT id FROM carts WHERE session_id=?", (session_id,))
    session_cart = c.fetchone()

    if session_cart:
        session_cart_id = session_cart[0]

        if user_cart:
            user_cart_id = user_cart[0]
            # Fusion des articles
            c.execute("SELECT painting_id, quantity FROM cart_items WHERE cart_id=?", (session_cart_id,))
            items = c.fetchall()
            for painting_id, qty in items:
                c.execute("SELECT quantity FROM cart_items WHERE cart_id=? AND painting_id=?",
                          (user_cart_id, painting_id))
                row = c.fetchone()
                if row:
                    c.execute("UPDATE cart_items SET quantity=? WHERE cart_id=? AND painting_id=?",
                              (row[0]+qty, user_cart_id, painting_id))
                else:
                    c.execute("INSERT INTO cart_items (cart_id, painting_id, quantity) VALUES (?, ?, ?)",
                              (user_cart_id, painting_id, qty))
            # Supprime l’ancien panier de session
            c.execute("DELETE FROM cart_items WHERE cart_id=?", (session_cart_id,))
            c.execute("DELETE FROM carts WHERE id=?", (session_cart_id,))
        else:
            # Associe le panier de session à l'utilisateur
            c.execute("UPDATE carts SET user_id=? WHERE id=?", (user_id, session_cart_id))

    conn.commit()
    conn.close()

# Initialisation et migration

init_users_table()
init_favorites_table()
migrate_db()
migrate_orders_db()
migrate_orders_user()
migrate_users_role()

# Définir l'administrateur
set_admin_user('coco.cayre@gmail.com')



# --------------------------------
# UTILITAIRES
# --------------------------------
def get_paintings():
    conn = sqlite3.connect(DB_PATH)
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
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    return result and result[0] == 'admin'

def require_admin(f):
    """Décorateur pour protéger les routes admin"""
    from functools import wraps
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                      (name, email, hashed_password))
            conn.commit()
            conn.close()
            flash("Inscription réussie !")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            flash("Cet email est déjà utilisé.")
            return redirect(url_for('register'))

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Vérifier utilisateur
        c.execute("SELECT id, password FROM users WHERE email=?", (email,))
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
        c.execute("SELECT id, session_id FROM carts WHERE user_id=?", (user_id,))
        user_cart = c.fetchone()

        if user_cart:
            # Panier utilisateur existant → récupérer session_id
            user_cart_session = user_cart[1]
        else:
            # Pas encore de panier user → en créer un
            user_cart_session = str(uuid.uuid4())
            c.execute("INSERT INTO carts (session_id, user_id) VALUES (?, ?)",
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
    conn = sqlite3.connect(DB_PATH)
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

# Page de détail
@app.route("/expo_detail/<int:expo_id>")
def expo_detail_page(expo_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM exhibitions WHERE id=?", (expo_id,))
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


# -----------------------------
# Éditer une exhibition
# -----------------------------
# ------------------- ROUTES EXPOSITIONS -------------------

# Liste des exhibitions
@app.route("/admin/exhibitions")
def admin_exhibitions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM exhibitions ORDER BY create_date DESC")
    exhibitions = c.fetchall()
    conn.close()
    return render_template("admin/admin_exhibitions.html", exhibitions=exhibitions, active="exhibitions")


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
        description = request.form.get("description")
        file = request.files.get("image")

        image_filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config['EXPO_UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['EXPO_UPLOAD_FOLDER'], filename))
            image_filename = filename

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO exhibitions (title, location, date, description, image)
            VALUES (?, ?, ?, ?, ?)
        """, (title, location, date, description, image_filename))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_exhibitions"))

    return render_template(
        "admin/form_exhibition.html",
        action="Ajouter",
        google_places_key=google_places_key
    )



@app.route("/admin/exhibitions/edit/<int:exhibition_id>", methods=["GET", "POST"])
def edit_exhibition(exhibition_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM exhibitions WHERE id=?", (exhibition_id,))
    exhibition = c.fetchone()

    google_places_key = get_setting("google_places_key") or ""

    if request.method == "POST":
        title = request.form["title"]
        location = request.form["location"]
        date = request.form["date"]
        description = request.form.get("description")
        file = request.files.get("image")

        image_filename = exhibition[5]  # Garde l'ancienne image si pas de nouvelle upload
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config['EXPO_UPLOAD_FOLDER'], exist_ok=True)
            file.save(os.path.join(app.config['EXPO_UPLOAD_FOLDER'], filename))
            image_filename = filename

        c.execute("""
            UPDATE exhibitions
            SET title=?, location=?, date=?, description=?, image=?
            WHERE id=?
        """, (title, location, date, description, image_filename, exhibition_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_exhibitions"))

    conn.close()
    return render_template(
        "admin/form_exhibition.html",
        exhibition=exhibition,
        action="Éditer",
        google_places_key=google_places_key  # ← clé dynamique passée au template
    )

# Supprimer une exhibition
@app.route("/admin/exhibitions/remove/<int:exhibition_id>", methods=["POST"])
def remove_exhibition(exhibition_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Supprimer l'image du dossier si elle existe
    c.execute("SELECT image FROM exhibitions WHERE id=?", (exhibition_id,))
    image = c.fetchone()
    if image and image[0]:
        image_path = os.path.join(app.config['EXPO_UPLOAD_FOLDER'], image[0])
        if os.path.exists(image_path):
            os.remove(image_path)

    c.execute("DELETE FROM exhibitions WHERE id=?", (exhibition_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_exhibitions"))

# ---------------------------------------------------------
# AJOUTER UN ARTICLE AU PANIER
# ---------------------------------------------------------
@app.route('/add_to_cart/<int:painting_id>')
def add_to_cart(painting_id):
    cart_id, session_id = get_or_create_cart()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Vérifie si l'article existe déjà
    c.execute("SELECT quantity FROM cart_items WHERE cart_id=? AND painting_id=?", (cart_id, painting_id))
    row = c.fetchone()
    if row:
        c.execute("UPDATE cart_items SET quantity=? WHERE cart_id=? AND painting_id=?", (row[0]+1, cart_id, painting_id))
    else:
        c.execute("INSERT INTO cart_items (cart_id, painting_id, quantity) VALUES (?, ?, 1)", (cart_id, painting_id))

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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT quantity FROM cart_items WHERE cart_id=? AND painting_id=?", (cart_id, painting_id))
    row = c.fetchone()
    if row:
        new_qty = row[0] - 1
        if new_qty <= 0:
            c.execute("DELETE FROM cart_items WHERE cart_id=? AND painting_id=?", (cart_id, painting_id))
        else:
            c.execute("UPDATE cart_items SET quantity=? WHERE cart_id=? AND painting_id=?", (new_qty, cart_id, painting_id))

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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("DELETE FROM cart_items WHERE cart_id=? AND painting_id=?", (cart_id, painting_id))

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
    conn = sqlite3.connect(DB_PATH)
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

    conn = sqlite3.connect(DB_PATH)
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
    address = order.get("address", "")  # Sécurisé
    total_price = order["total_price"]
    items = order["items"]

    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()

        # ----------------------------------------------------------
        # 1) Vérifier si l'utilisateur existe déjà
        # ----------------------------------------------------------
        c.execute("SELECT id FROM users WHERE email=?", (email,))
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
        c.execute("DELETE FROM cart_items WHERE cart_id=?", (cart_id,))

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
        "email_sender"
    ]

    if request.method == "POST":
        for key in settings_keys:
            value = request.form.get(key, "")
            set_setting(key, value)
        flash("Paramètres mis à jour avec succès !", "success")
        return redirect(url_for("admin_settings_page"))

    settings_values = {key: get_setting(key) or "" for key in settings_keys}

    return render_template(
        "admin/admin_settings.html",  # <-- chemin corrigé
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

    conn = sqlite3.connect(DB_PATH)
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
        description = request.form.get('description', '')  # <-- Récupère la description ou '' si vide

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

            create_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO paintings (name, image, price, quantity, description, create_date) VALUES (?, ?, ?, ?, ?, ?)",
                (name, image_path, price, quantity, description, create_date)
            )
            conn.commit()
            conn.close()

            flash('Peinture ajoutée avec succès !')
            return redirect(url_for('home'))

        else:
            flash('Fichier non autorisé. Seules les images sont acceptées.')
            return redirect(request.url)

    return render_template('admin/add_painting.html')


@app.context_processor
def inject_cart():
    session_id = request.cookies.get("cart_session")
    user_id = session.get("user_id")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # --- PANIER ---
    if user_id:
        c.execute("SELECT id FROM carts WHERE user_id=?", (user_id,))
        row = c.fetchone()
        cart_id = row[0] if row else None
    else:
        if session_id:
            c.execute("SELECT id FROM carts WHERE session_id=?", (session_id,))
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
        c.execute("SELECT painting_id FROM favorites WHERE user_id=?", (user_id,))
        favorite_ids = [row[0] for row in c.fetchall()]

    # --- NOTIFICATIONS ADMIN ---
    new_notifications_count = 0
    if is_admin():
        c.execute("SELECT COUNT(*) FROM notifications WHERE user_id IS ? AND is_read=0", (None,))
        new_notifications_count = c.fetchone()[0]

    conn.close()

    return dict(
        cart_items=cart_items,
        cart_count=total_qty,
        favorite_ids=favorite_ids,
        is_admin=is_admin(),
        new_notifications_count=new_notifications_count  # ← ajouté ici
    )


@app.route("/admin/notifications")
def admin_notifications():
    if not is_admin():
        return redirect(url_for('index'))

    with sqlite3.connect(DB_PATH) as conn:
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
        return redirect(url_for("index"))

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Mettre la notification comme lue
        c.execute("UPDATE notifications SET is_read=1 WHERE id=?", (notif_id,))
        # Récupérer l'URL pour redirection
        c.execute("SELECT url FROM notifications WHERE id=?", (notif_id,))
        row = c.fetchone()
        redirect_url = row[0] if row and row[0] else url_for("admin_notifications")

    return redirect(redirect_url)


# --------------------------------
# ROUTE GALERIE
# --------------------------------
@app.route('/galerie')
def galerie():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, image, price FROM paintings ORDER BY id DESC")
    paintings = c.fetchall()
    conn.close()
    return render_template('galerie.html', paintings=paintings)

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

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Récupérer les infos de l'utilisateur connecté
    c.execute("SELECT id, name, email, create_date FROM users WHERE id=?", (user_id,))
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

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO favorites (user_id, painting_id) VALUES (?, ?)", (user_id, painting_id))
        conn.commit()
        flash("Ajouté aux favoris !")
    except sqlite3.IntegrityError:
        flash("Cette peinture est déjà dans vos favoris.")
    finally:
        conn.close()

    return redirect(request.referrer or url_for('home'))

@app.route('/remove_favorite/<int:painting_id>')
def remove_favorite(painting_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Vous devez être connecté.")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("DELETE FROM favorites WHERE user_id=? AND painting_id=?", (user_id, painting_id))
    conn.commit()
    conn.close()

    flash("Retiré des favoris !")
    return redirect(request.referrer or url_for('home'))

@app.route('/is_favorite/<int:painting_id>')
def is_favorite(painting_id):
    user_id = session.get("user_id")
    if not user_id:
        return {'is_favorite': False}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT 1 FROM favorites WHERE user_id=? AND painting_id=?", (user_id, painting_id))
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
    conn = sqlite3.connect(DB_PATH)
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
    
    conn.close()
    
    return render_template('admin/admin_dashboard.html',
                         total_paintings=total_paintings,
                         total_orders=total_orders,
                         total_revenue=total_revenue,
                         total_users=total_users,
                         recent_orders=recent_orders,
                         out_of_stock=out_of_stock,
                         active="dashboard")

@app.route('/admin/paintings')
@require_admin
def admin_paintings():
    """Gestion des peintures"""
    paintings = get_paintings()
    return render_template('admin/admin_paintings.html', paintings=paintings, active="paintings")

@app.route('/admin/painting/remove/<int:painting_id>', methods=['POST'])
def remove_painting(painting_id):
    if not is_admin():
        return redirect(url_for('index'))

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM paintings WHERE id=?", (painting_id,))
        conn.commit()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/painting/edit/<int:painting_id>', methods=['GET', 'POST'])
@require_admin
def edit_painting(painting_id):
    """Éditer une peinture"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Récupérer la peinture
    c.execute("SELECT id, name, image, price, quantity, description, create_date FROM paintings WHERE id=?", (painting_id,))
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
        
        if not name or price == '' or quantity == '':
            flash("Tous les champs sont obligatoires.")
            conn.close()
            return redirect(url_for('edit_painting', painting_id=painting_id))
        
        try:
            price = float(price)
            quantity = int(quantity)

            # Gestion du fichier image
            file = request.files.get('image')
            image_path = painting[2]  # valeur par défaut : garder l'image actuelle
            if file and file.filename and allowed_file(file.filename):
                # Générer un nom de fichier unique pour éviter collisions
                filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)

                # Supprimer l'ancienne image si elle existe et n'est pas la même
                try:
                    old_image_rel = painting[2] or ""
                    if old_image_rel:
                        old_image_path = old_image_rel
                        if not old_image_path.startswith("static") and not os.path.isabs(old_image_path):
                            old_image_path = os.path.join('static', old_image_path)
                        if os.path.exists(old_image_path) and os.path.abspath(old_image_path) != os.path.abspath(save_path):
                            os.remove(old_image_path)
                except Exception:
                    pass

                # Stocker le chemin relatif cohérent
                image_path = f"Images/{filename}"

            # Update BDD
            c.execute(
                "UPDATE paintings SET name=?, price=?, quantity=?, image=?, description=? WHERE id=?",
                (name, price, quantity, image_path, description, painting_id)
            )
            conn.commit()
            flash("Peinture mise à jour avec succès !")
            conn.close()
            return redirect(url_for('admin_paintings'))
        
        except ValueError:
            flash("Prix et quantité doivent être des nombres.")
            conn.close()
            return redirect(url_for('edit_painting', painting_id=painting_id))
    
    conn.close()
    return render_template('admin/edit_painting.html', painting=painting)

@app.route('/admin/painting/delete/<int:painting_id>')
@require_admin
def delete_painting(painting_id):
    """Supprimer une peinture"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT image FROM paintings WHERE id=?", (painting_id,))
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
        c.execute("DELETE FROM paintings WHERE id=?", (painting_id,))
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
    conn = sqlite3.connect(DB_PATH)
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
    return render_template('admin/admin_orders.html', orders=orders_list, all_items=all_items, active="orders")

@app.route("/order/<int:order_id>")
def order_status(order_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Récupérer la commande
    c.execute("SELECT id, customer_name, email, address, total_price, status FROM orders WHERE id=?", (order_id,))
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
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()
    
    flash(f"Commande #{order_id} mise à jour : {status}")
    return redirect(url_for('admin_orders'))


@app.route("/admin/orders/<int:order_id>")
def admin_order_detail(order_id):
    if not is_admin():
        return redirect(url_for("index"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Récupérer la commande
    c.execute("SELECT id, customer_name, email, address, total_price, order_date, status FROM orders WHERE id=?", (order_id,))
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

    return render_template("admin/admin_order_detail.html", order=order, items=items)


@app.route('/admin/users')
@require_admin
def admin_users():
    """Gestion des utilisateurs avec recherche et filtre par rôle"""
    q = request.args.get('q', '').strip().lower()
    role = request.args.get('role', '').strip().lower()
    
    conn = sqlite3.connect(DB_PATH)
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

    return render_template('admin/admin_users.html', users=users, active="users")

@app.route('/admin/users/export')
@require_admin
def export_users():
    """Export des utilisateurs filtrés/recherchés au format Excel"""
    q = request.args.get('q', '').strip().lower()
    role_filter = request.args.get('role')

    conn = sqlite3.connect(DB_PATH)
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
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Ne pas laisser supprimer l'admin principal
    c.execute("SELECT email FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    
    if user and user[0] == 'coco.cayre@gmail.com' and role != 'admin':
        flash("Impossible de retirer le rôle admin à l'administrateur principal.")
        conn.close()
        return redirect(url_for('admin_users'))
    
    c.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE role=?", (role,))
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
    Envoie un email de confirmation de commande au client avec design type site et images intégrées en pièce jointe (CID).
    Le bouton permet d'accéder à la page de suivi de la commande.
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import os

    # --- CONFIGURATION SMTP DYNAMIQUE ---
    SMTP_SERVER = get_setting("smtp_server") or "smtp.gmail.com"
    SMTP_PORT = int(get_setting("smtp_port") or 587)
    SMTP_USER = get_setting("email_sender") or "coco.cayre@gmail.com"
    SMTP_PASSWORD = get_setting("smtp_password") or "motdepassepardefaut"


    # --- CONSTRUCTION DU MESSAGE ---
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = customer_email
    msg['Subject'] = f"Confirmation de votre commande #{order_id}"

    # Corps du mail en HTML avec CID
    items_html = ""
    for i, item in enumerate(items):
        cid = f"item{i}"  # identifiant unique pour l'image
        image_path = os.path.join("static", item[2])  # chemin local vers l'image
        items_html += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid #ddd;">
                <img src="cid:{cid}" alt="{item[1]}" style="width:60px; height:60px; object-fit:cover; border-radius:8px;">
            </td>
            <td style="padding:10px; border-bottom:1px solid #ddd;">
                {item[1]}<br>
                Quantité: {item[4]}
            </td>
            <td style="padding:10px; border-bottom:1px solid #ddd; text-align:right;">
                {item[3]} €
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

    # Lien complet vers la page de suivi (mettre ton domaine réel en prod)
    track_url = f"http://127.0.0.1:5000/order/{order_id}"


    body = f"""
    <html>
    <body style="font-family:Poppins, sans-serif; background:#e0f2ff; padding:20px;">
        <div style="max-width:600px; margin:auto; background:white; border-radius:15px; padding:20px; box-shadow:0 5px 15px rgba(0,0,0,0.1);">
            <h2 style="color:#1E3A8A;">Bonjour {customer_name},</h2>
            <p>Merci pour votre commande <strong>#{order_id}</strong>.</p>
            
            <table style="width:100%; border-collapse:collapse; margin-top:20px;">
                {items_html}
            </table>

            <p style="text-align:right; font-weight:bold; font-size:16px; margin-top:20px;">
                Total : {total_price} €
            </p>

            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-top:20px;">
                <tr>
                    <td align="center" bgcolor="#1E3A8A" style="border-radius:8px;">
                        <a href="{track_url}" target="_blank" style="
                            display:inline-block;
                            padding:12px 20px;
                            font-size:16px;
                            color:#ffffff;
                            text-decoration:none;
                            font-weight:600;
                        ">Voir votre commande</a>
                    </td>
                </tr>
            </table>

            <p style="margin-top:30px;">Votre commande sera traitée rapidement.<br>Cordialement,<br>JB Art</p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

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
# LANCEMENT DE L'APPLICATION
# --------------------------------
if __name__ == "__main__":
    app.run(debug=True)
    migrate_db()
    print("Migration terminée ✅")
