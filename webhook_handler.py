"""
Webhook handler pour synchronisation Dashboard → Site Vitrine
Gère les mises à jour en temps réel depuis le Dashboard central
"""

from flask import Blueprint, request, jsonify
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional

from supabase_client import get_admin_client

# Configuration du logging
logger = logging.getLogger('dashboard_webhook')

# Blueprint pour les webhooks
webhook_bp = Blueprint('webhooks', __name__, url_prefix='/webhook')

# Secret pour validation signature (à définir en variable d'environnement)
import os
WEBHOOK_SECRET = os.environ.get('DASHBOARD_WEBHOOK_SECRET', '')

if not WEBHOOK_SECRET:
    logger.warning("⚠️  DASHBOARD_WEBHOOK_SECRET non définie - validation signature désactivée")
else:
    logger.info("✅ Webhook secret configuré")


def validate_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Valide la signature HMAC du webhook
    
    Args:
        payload: Corps de la requête (bytes)
        signature: Signature envoyée par le Dashboard (format: sha256=xxx)
    
    Returns:
        True si signature valide, False sinon
    """
    # Vérifier si le mode dev est explicitement activé
    dev_mode = os.environ.get('WEBHOOK_DEV_MODE', '').lower() == 'true'
    
    if not WEBHOOK_SECRET:
        if dev_mode:
            logger.warning("⚠️  Mode DEV: Validation signature ignorée (WEBHOOK_SECRET non défini)")
            return True
        else:
            logger.error("❌ WEBHOOK_SECRET non défini et WEBHOOK_DEV_MODE non activé - rejet sécurisé")
            return False
    
    if not signature:
        logger.error("Signature manquante dans le header")
        return False
    
    # Extraire le hash (format: sha256=xxx)
    if not signature.startswith('sha256='):
        logger.error(f"Format signature invalide: {signature[:20]}")
        return False
    
    expected_signature = signature[7:]  # Retirer 'sha256='
    
    # Calculer le HMAC
    computed = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Comparaison constant-time
    is_valid = hmac.compare_digest(computed, expected_signature)
    
    if not is_valid:
        logger.error("Signature invalide")
    
    return is_valid


def refresh_artist_cache(artist_id: int) -> bool:
    """
    Rafraîchit le cache d'un artiste depuis Supabase
    
    Args:
        artist_id: ID de l'artiste
    
    Returns:
        True si rafraîchissement réussi
    """
    try:
        client = get_admin_client()
        artist = client.select(
            'template_artists',
            columns='*',
            filters={'id': artist_id}
        )
        
        if artist:
            logger.info(f"Cache artiste {artist_id} rafraîchi")
            # Ici on pourrait mettre à jour un cache Redis, memcached, etc.
            return True
        else:
            logger.warning(f"Artiste {artist_id} non trouvé pour rafraîchissement cache")
            return False
    except Exception as e:
        logger.error(f"Erreur rafraîchissement cache artiste {artist_id}: {e}")
        return False


@webhook_bp.route('/dashboard', methods=['POST'])
def handle_dashboard_webhook():
    """
    Endpoint webhook pour recevoir les mises à jour du Dashboard
    
    Headers attendus:
        X-Dashboard-Signature: sha256=xxx (HMAC du payload)
    
    Body (JSON):
        {
            "event": "artist.updated" | "artist.created" | "artist.deleted",
            "artist_id": 123,
            "data": {...},  # Données modifiées
            "timestamp": "2025-12-10T22:00:00Z"
        }
    
    Returns:
        200: Webhook traité
        401: Signature invalide
        400: Payload invalide
        500: Erreur traitement
    """
    # Récupérer la signature
    signature = request.headers.get('X-Dashboard-Signature', '')
    
    # Valider la signature
    if not validate_webhook_signature(request.data, signature):
        logger.error("Webhook rejeté: signature invalide")
        return jsonify({
            'error': 'Signature invalide',
            'received': False
        }), 401
    
    # Parser le payload
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'Payload vide'}), 400
    except Exception as e:
        logger.error(f"Erreur parsing payload webhook: {e}")
        return jsonify({'error': 'Payload JSON invalide'}), 400
    
    # Extraire les données
    event_type = payload.get('event')
    artist_id = payload.get('artist_id')
    data = payload.get('data', {})
    timestamp = payload.get('timestamp')
    
    logger.info(
        f"Webhook reçu: {event_type} | artist_id={artist_id} | timestamp={timestamp}"
    )
    
    # Traiter selon le type d'événement
    try:
        if event_type == 'artist.updated':
            # Rafraîchir le cache de l'artiste
            success = refresh_artist_cache(artist_id)
            
            if success:
                logger.info(f"Artiste {artist_id} mis à jour via webhook")
                return jsonify({
                    'received': True,
                    'event': event_type,
                    'artist_id': artist_id,
                    'action': 'cache_refreshed'
                }), 200
            else:
                return jsonify({
                    'received': True,
                    'event': event_type,
                    'artist_id': artist_id,
                    'action': 'refresh_failed'
                }), 500
        
        elif event_type == 'artist.created':
            # Nouvel artiste créé sur le Dashboard
            logger.info(f"Nouvel artiste {artist_id} créé via webhook")
            refresh_artist_cache(artist_id)
            
            return jsonify({
                'received': True,
                'event': event_type,
                'artist_id': artist_id,
                'action': 'acknowledged'
            }), 200
        
        elif event_type == 'artist.deleted':
            # Artiste supprimé sur le Dashboard
            logger.info(f"Artiste {artist_id} supprimé via webhook")
            # Invalider le cache
            
            return jsonify({
                'received': True,
                'event': event_type,
                'artist_id': artist_id,
                'action': 'cache_invalidated'
            }), 200
        
        elif event_type == 'artist.approved':
            # Artiste approuvé
            logger.info(f"Artiste {artist_id} approuvé via webhook")
            refresh_artist_cache(artist_id)
            
            return jsonify({
                'received': True,
                'event': event_type,
                'artist_id': artist_id,
                'action': 'cache_refreshed'
            }), 200
        
        elif event_type == 'artist.rejected':
            # Artiste rejeté
            logger.info(f"Artiste {artist_id} rejeté via webhook")
            refresh_artist_cache(artist_id)
            
            return jsonify({
                'received': True,
                'event': event_type,
                'artist_id': artist_id,
                'action': 'cache_refreshed'
            }), 200
        
        else:
            logger.warning(f"Type d'événement inconnu: {event_type}")
            return jsonify({
                'received': True,
                'event': event_type,
                'action': 'ignored',
                'reason': 'unknown_event_type'
            }), 200
    
    except Exception as e:
        logger.error(f"Erreur traitement webhook {event_type}: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'received': True,
            'event': event_type,
            'error': str(e)
        }), 500


@webhook_bp.route('/dashboard/test', methods=['POST'])
def test_dashboard_webhook():
    """
    Endpoint de test pour vérifier la configuration webhook
    
    Returns:
        200: Configuration OK
        401: Signature invalide
    """
    signature = request.headers.get('X-Dashboard-Signature', '')
    
    if not validate_webhook_signature(request.data, signature):
        return jsonify({
            'ok': False,
            'error': 'Signature invalide',
            'hint': 'Vérifiez DASHBOARD_WEBHOOK_SECRET'
        }), 401
    
    payload = request.get_json() or {}
    
    logger.info(f"Test webhook reçu: {payload}")
    
    return jsonify({
        'ok': True,
        'message': 'Webhook configuré correctement',
        'payload_received': payload,
        'signature_valid': True
    }), 200


@webhook_bp.route('/dashboard/ping', methods=['GET', 'POST'])
def ping_webhook():
    """
    Endpoint ping pour vérifier que le webhook est accessible
    
    Returns:
        200: Service actif
    """
    return jsonify({
        'ok': True,
        'service': 'webhook_handler',
        'status': 'active',
        'endpoints': {
            'main': '/webhook/dashboard',
            'test': '/webhook/dashboard/test',
            'ping': '/webhook/dashboard/ping'
        }
    }), 200
