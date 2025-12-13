"""
Service de synchronisation: Template → Dashboard
Récupère les données du Template et les stocke dans les bonnes tables
Adapté à Flask + PostgreSQL (psycopg2) sans ORM
"""

import requests
import psycopg2
from psycopg2 import sql
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class TemplateSyncService:
    """Synchronise les données du Template vers le Dashboard"""
    
    def __init__(self, db_conn, template_url, api_key, site_id):
        """
        Args:
            db_conn: Connexion PostgreSQL (psycopg2)
            template_url: URL du Template (ex: https://jb.artworksdigital.fr)
            api_key: Clé API d'export
            site_id: ID du site au Dashboard
        """
        self.db_conn = db_conn
        self.template_url = template_url.rstrip('/')
        self.api_key = api_key
        self.site_id = site_id
        self.timeout = 30
        self.headers = {'X-API-Key': api_key}
        self.sync_log = []
    
    def get_from_template(self, endpoint, params=None):
        """Récupère les données du Template"""
        url = f"{self.template_url}/api/export{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Erreur Template {endpoint}: {e}")
            raise
    
    def sync_paintings(self):
        """Synchronise les peintures: Template → Dashboard"""
        try:
            data = self.get_from_template('/paintings')
            paintings = data.get('paintings', [])
            
            cursor = self.db_conn.cursor()
            synced = 0
            
            for p in paintings:
                # Vérifier si existe déjà
                cursor.execute("""
                    SELECT id FROM paintings 
                    WHERE site_id=%s AND template_id=%s
                """, (self.site_id, p['id']))
                
                existing = cursor.fetchone()
                
                if existing:
                    # UPDATE
                    cursor.execute("""
                        UPDATE paintings 
                        SET name=%s, price=%s, image=%s, status=%s, 
                            category=%s, technique=%s, year=%s, quantity=%s
                        WHERE site_id=%s AND template_id=%s
                    """, (
                        p['name'], p['price'], p['image'], p['status'],
                        p.get('category'), p.get('technique'), p.get('year'), 
                        p.get('quantity', 1),
                        self.site_id, p['id']
                    ))
                else:
                    # INSERT
                    cursor.execute("""
                        INSERT INTO paintings 
                        (site_id, template_id, name, price, image, status, 
                         category, technique, year, quantity, create_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        self.site_id, p['id'], p['name'], p['price'], p['image'],
                        p['status'], p.get('category'), p.get('technique'), 
                        p.get('year'), p.get('quantity', 1), datetime.now().isoformat()
                    ))
                
                synced += 1
            
            self.db_conn.commit()
            cursor.close()
            
            self.log('paintings', 'success', synced)
            return {'success': True, 'count': synced}
            
        except Exception as e:
            self.db_conn.rollback()
            self.log('paintings', 'error', 0, str(e))
            logger.error(f"Erreur sync paintings: {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_users(self):
        """Synchronise les utilisateurs avec leurs rôles"""
        try:
            data = self.get_from_template('/users')
            users = data.get('users', [])
            
            cursor = self.db_conn.cursor()
            synced = 0
            
            for u in users:
                cursor.execute("""
                    SELECT id FROM users 
                    WHERE site_id=%s AND template_id=%s
                """, (self.site_id, u['id']))
                
                existing = cursor.fetchone()
                
                if existing:
                    # UPDATE
                    cursor.execute("""
                        UPDATE users 
                        SET name=%s, email=%s, role=%s
                        WHERE site_id=%s AND template_id=%s
                    """, (
                        u['name'], u['email'], u['role'],
                        self.site_id, u['id']
                    ))
                else:
                    # INSERT - Attention: password doit être hashé mais on le laisse vide
                    cursor.execute("""
                        INSERT INTO users 
                        (site_id, template_id, name, email, password, role, create_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        self.site_id, u['id'], u['name'], u['email'],
                        '', u['role'], datetime.now().isoformat()
                    ))
                
                synced += 1
            
            self.db_conn.commit()
            cursor.close()
            
            self.log('users', 'success', synced)
            return {'success': True, 'count': synced}
            
        except Exception as e:
            self.db_conn.rollback()
            self.log('users', 'error', 0, str(e))
            logger.error(f"Erreur sync users: {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_orders(self):
        """Synchronise les commandes"""
        try:
            data = self.get_from_template('/orders')
            orders = data.get('orders', [])
            
            cursor = self.db_conn.cursor()
            synced = 0
            
            for o in orders:
                cursor.execute("""
                    SELECT id FROM orders 
                    WHERE site_id=%s AND id=%s
                """, (self.site_id, o['id']))
                
                existing = cursor.fetchone()
                
                if existing:
                    # UPDATE
                    cursor.execute("""
                        UPDATE orders 
                        SET customer_name=%s, email=%s, total_price=%s, status=%s
                        WHERE site_id=%s AND id=%s
                    """, (
                        o['customer_name'], o['email'], o['total_price'],
                        o['status'], self.site_id, o['id']
                    ))
                else:
                    # INSERT
                    cursor.execute("""
                        INSERT INTO orders 
                        (site_id, customer_name, email, address, total_price, status, order_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        self.site_id, o['customer_name'], o['email'],
                        '', o['total_price'], o['status'], 
                        o.get('order_date', datetime.now().isoformat())
                    ))
                    
                    # Items de la commande
                    order_id = cursor.lastrowid if hasattr(cursor, 'lastrowid') else o['id']
                    for item in o.get('items', []):
                        cursor.execute("""
                            INSERT INTO order_items 
                            (order_id, painting_id, quantity, price)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            order_id, item['painting_id'], 
                            item['quantity'], item['unit_price']
                        ))
                
                synced += 1
            
            self.db_conn.commit()
            cursor.close()
            
            self.log('orders', 'success', synced)
            return {'success': True, 'count': synced}
            
        except Exception as e:
            self.db_conn.rollback()
            self.log('orders', 'error', 0, str(e))
            logger.error(f"Erreur sync orders: {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_settings(self):
        """Synchronise les settings du Template"""
        try:
            data = self.get_from_template('/settings')
            settings = data.get('settings', [])
            
            cursor = self.db_conn.cursor()
            synced = 0
            
            for s in settings:
                # Les settings sont globaux, pas site_id
                cursor.execute("""
                    SELECT id FROM settings WHERE key=%s
                """, (s['key'],))
                
                existing = cursor.fetchone()
                
                if existing and 'secret' not in s['key'].lower():
                    # UPDATE (ne pas update les secrets!)
                    cursor.execute("""
                        UPDATE settings SET value=%s WHERE key=%s
                    """, (s['value'], s['key']))
                    synced += 1
                elif not existing and 'secret' not in s['key'].lower():
                    # INSERT
                    cursor.execute("""
                        INSERT INTO settings (key, value) VALUES (%s, %s)
                    """, (s['key'], s['value']))
                    synced += 1
            
            self.db_conn.commit()
            cursor.close()
            
            self.log('settings', 'success', synced)
            return {'success': True, 'count': synced}
            
        except Exception as e:
            self.db_conn.rollback()
            self.log('settings', 'error', 0, str(e))
            logger.error(f"Erreur sync settings: {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_all(self):
        """Synchronise TOUT"""
        results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'paintings': self.sync_paintings(),
            'users': self.sync_users(),
            'orders': self.sync_orders(),
            'settings': self.sync_settings()
        }
        
        # Enregistrer le log
        self.save_sync_log(results)
        
        return results
    
    def log(self, entity, status, count, error=None):
        """Enregistre un événement de sync"""
        self.sync_log.append({
            'entity': entity,
            'status': status,
            'count': count,
            'error': error
        })
    
    def save_sync_log(self, results):
        """Sauvegarde le log de synchronisation"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO template_sync_log 
                (site_id, sync_type, status, records_processed, errors, details)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                self.site_id,
                'full_sync',
                'success' if results['success'] else 'error',
                sum(r.get('count', 0) for r in results.values() if isinstance(r, dict)),
                len([r for r in self.sync_log if r['status'] == 'error']),
                json.dumps(self.sync_log)
            ))
            self.db_conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Erreur save_sync_log: {e}")
