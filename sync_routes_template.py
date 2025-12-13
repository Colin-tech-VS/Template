"""
Routes Flask pour synchronisation Template → Dashboard
À intégrer dans ton app Flask du Dashboard
"""

from flask import Blueprint, request, jsonify
import psycopg2
from datetime import datetime
import logging
from template_sync_service import TemplateSyncService

logger = logging.getLogger(__name__)

# Créer le blueprint
sync_bp = Blueprint('sync', __name__, url_prefix='/api/sync')

# Adapter selon ta configuration BD
DB_CONFIG = {
    'host': 'votre-supabase-host.supabase.co',
    'user': 'postgres',
    'password': 'votre-password',
    'database': 'postgres',
    'port': 5432
}

def get_db():
    """Connexion à PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)

@sync_bp.route('/template/<int:site_id>', methods=['POST'])
def sync_template(site_id):
    """
    POST /api/sync/template/{site_id}
    Lance la synchronisation manuelle d'un Template
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Récupérer les infos du site
        cursor.execute("""
            SELECT url, api_key FROM sites WHERE id=%s
        """, (site_id,))
        
        result = cursor.fetchone()
        if not result:
            cursor.close()
            db.close()
            return jsonify({'error': 'Site not found'}), 404
        
        template_url, api_key = result
        cursor.close()
        
        # Lancer la synchronisation
        sync = TemplateSyncService(db, template_url, api_key, site_id)
        sync_result = sync.sync_all()
        
        db.close()
        
        return jsonify(sync_result)
        
    except Exception as e:
        logger.error(f"Erreur sync_template: {e}")
        return jsonify({'error': str(e)}), 500

@sync_bp.route('/template/<int:site_id>/paintings', methods=['POST'])
def sync_paintings_only(site_id):
    """
    POST /api/sync/template/{site_id}/paintings
    Synchronise JUSTE les peintures
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("SELECT url, api_key FROM sites WHERE id=%s", (site_id,))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            db.close()
            return jsonify({'error': 'Site not found'}), 404
        
        template_url, api_key = result
        cursor.close()
        
        sync = TemplateSyncService(db, template_url, api_key, site_id)
        sync_result = sync.sync_paintings()
        
        db.close()
        return jsonify(sync_result)
        
    except Exception as e:
        logger.error(f"Erreur sync_paintings_only: {e}")
        return jsonify({'error': str(e)}), 500

@sync_bp.route('/template/<int:site_id>/users', methods=['POST'])
def sync_users_only(site_id):
    """
    POST /api/sync/template/{site_id}/users
    Synchronise JUSTE les utilisateurs
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("SELECT url, api_key FROM sites WHERE id=%s", (site_id,))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            db.close()
            return jsonify({'error': 'Site not found'}), 404
        
        template_url, api_key = result
        cursor.close()
        
        sync = TemplateSyncService(db, template_url, api_key, site_id)
        sync_result = sync.sync_users()
        
        db.close()
        return jsonify(sync_result)
        
    except Exception as e:
        logger.error(f"Erreur sync_users_only: {e}")
        return jsonify({'error': str(e)}), 500

@sync_bp.route('/template/<int:site_id>/orders', methods=['POST'])
def sync_orders_only(site_id):
    """
    POST /api/sync/template/{site_id}/orders
    Synchronise JUSTE les commandes
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("SELECT url, api_key FROM sites WHERE id=%s", (site_id,))
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            db.close()
            return jsonify({'error': 'Site not found'}), 404
        
        template_url, api_key = result
        cursor.close()
        
        sync = TemplateSyncService(db, template_url, api_key, site_id)
        sync_result = sync.sync_orders()
        
        db.close()
        return jsonify(sync_result)
        
    except Exception as e:
        logger.error(f"Erreur sync_orders_only: {e}")
        return jsonify({'error': str(e)}), 500

@sync_bp.route('/template/<int:site_id>/status', methods=['GET'])
def sync_status(site_id):
    """
    GET /api/sync/template/{site_id}/status
    Retourne l'historique des dernières synchros
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Dernière synchro
        cursor.execute("""
            SELECT synced_at, sync_type, status, records_processed, errors 
            FROM template_sync_log 
            WHERE site_id=%s 
            ORDER BY synced_at DESC 
            LIMIT 10
        """, (site_id,))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'timestamp': row[0].isoformat() if row[0] else None,
                'type': row[1],
                'status': row[2],
                'records': row[3],
                'errors': row[4]
            })
        
        cursor.close()
        db.close()
        
        return jsonify({
            'success': True,
            'logs': logs,
            'last_sync': logs[0] if logs else None
        })
        
    except Exception as e:
        logger.error(f"Erreur sync_status: {e}")
        return jsonify({'error': str(e)}), 500

# À ajouter dans ton app Flask principal:
# app.register_blueprint(sync_bp)
