"""
API Endpoints pour la gestion des artistes via Supabase REST API
Tous les endpoints utilisent PostgREST pour communiquer avec Supabase
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from supabase_client import get_public_client, get_admin_client

# Configuration du logging
logger = logging.getLogger('artists_api')

# Blueprint pour les routes artistes
artists_bp = Blueprint('artists', __name__, url_prefix='/api/artists')


def log_artist_action(
    artist_id: int,
    action: str,
    performed_by: Optional[str] = None,
    details: Optional[str] = None
):
    """
    Enregistre une action dans artworks_artist_actions
    
    Args:
        artist_id: ID de l'artiste
        action: Type d'action ('created', 'updated', 'approved', 'rejected', 'deleted')
        performed_by: Qui a effectué l'action
        details: Détails supplémentaires (JSON)
    """
    try:
        client = get_admin_client()
        action_data = {
            'artist_id': artist_id,
            'action': action,
            'action_date': datetime.utcnow().isoformat(),
            'performed_by': performed_by or 'system',
            'details': details
        }
        client.insert('artworks_artist_actions', action_data)
        logger.info(f"Action '{action}' enregistrée pour artiste {artist_id}")
    except Exception as e:
        logger.error(f"Erreur enregistrement action pour artiste {artist_id}: {e}")


@artists_bp.route('', methods=['POST'])
def create_artist():
    """
    POST /api/artists - Création d'un artiste
    
    Body (JSON):
        {
            "name": "Jean Dupont",
            "email": "jean@example.com",
            "phone": "+33612345678",
            "bio": "Artiste peintre",
            "website": "https://jean-dupont.art",
            "price": 500.00
        }
    
    Returns:
        201: Artiste créé avec données complètes
        400: Données invalides
        500: Erreur serveur
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Aucune donnée fournie'}), 400
        
        # Validation champs requis
        required_fields = ['name', 'email']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({
                'error': 'Champs manquants',
                'missing': missing_fields
            }), 400
        
        # Préparer les données artiste
        artist_data = {
            'name': data.get('name'),
            'email': data.get('email'),
            'phone': data.get('phone'),
            'bio': data.get('bio'),
            'website': data.get('website'),
            'price': data.get('price', 500.00),
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Insertion via client admin
        client = get_admin_client()
        result = client.insert('template_artists', artist_data)
        
        # Logger l'action 'created'
        if result and result.get('id'):
            log_artist_action(
                result['id'],
                'created',
                performed_by=data.get('created_by', 'system'),
                details=f"Artiste {result['name']} créé"
            )
        
        logger.info(f"Artiste créé: {result.get('id')} - {result.get('name')}")
        
        return jsonify({
            'success': True,
            'data': result
        }), 201
        
    except ValueError as e:
        logger.error(f"Erreur validation création artiste: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Erreur création artiste: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


@artists_bp.route('/<int:artist_id>', methods=['GET'])
def get_artist(artist_id: int):
    """
    GET /api/artists/:id - Lecture d'un artiste par ID
    
    Returns:
        200: Artiste trouvé avec toutes les colonnes
        404: Artiste non trouvé
        500: Erreur serveur
    """
    try:
        # Utiliser client public pour lecture
        client = get_public_client()
        
        # SELECT * avec filtre sur id
        results = client.select(
            'template_artists',
            columns='*',
            filters={'id': artist_id}
        )
        
        if not results:
            return jsonify({'error': 'Artiste non trouvé'}), 404
        
        artist = results[0]
        logger.info(f"Artiste récupéré: {artist_id} - {artist.get('name')}")
        
        return jsonify({
            'success': True,
            'data': artist
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur récupération artiste {artist_id}: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


@artists_bp.route('', methods=['GET'])
def list_artists():
    """
    GET /api/artists - Liste tous les artistes avec pagination et filtres
    
    Query params:
        - status: Filtrer par statut (pending, approved, rejected)
        - limit: Nombre de résultats (défaut: 50)
        - offset: Offset pour pagination (défaut: 0)
        - order: Tri (ex: "created_at.desc")
    
    Returns:
        200: Liste d'artistes
        500: Erreur serveur
    """
    try:
        # Récupérer paramètres de requête
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        order = request.args.get('order', 'created_at.desc')
        
        # Validation limit/offset
        if limit < 1 or limit > 200:
            return jsonify({'error': 'limit doit être entre 1 et 200'}), 400
        if offset < 0:
            return jsonify({'error': 'offset doit être >= 0'}), 400
        
        # Construire filtres
        filters = {}
        if status_filter:
            filters['status'] = status_filter
        
        # Récupération via client public
        client = get_public_client()
        results = client.select(
            'template_artists',
            columns='*',
            filters=filters if filters else None,
            order=order,
            limit=limit,
            offset=offset
        )
        
        logger.info(f"Liste artistes récupérée: {len(results)} résultats")
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results),
            'limit': limit,
            'offset': offset
        }), 200
        
    except ValueError as e:
        logger.error(f"Erreur validation paramètres liste artistes: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Erreur liste artistes: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


@artists_bp.route('/<int:artist_id>', methods=['PATCH'])
def update_artist(artist_id: int):
    """
    PATCH /api/artists/:id - Mise à jour d'un artiste
    
    Body (JSON): Champs à mettre à jour
        {
            "name": "Nouveau nom",
            "email": "nouveau@example.com",
            "price": 600.00,
            "bio": "Nouvelle bio"
        }
    
    Returns:
        200: Artiste mis à jour avec données complètes
        404: Artiste non trouvé
        400: Données invalides
        500: Erreur serveur
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Aucune donnée fournie'}), 400
        
        # Ajouter updated_at
        data['updated_at'] = datetime.utcnow().isoformat()
        
        # Mise à jour via client admin
        client = get_admin_client()
        result = client.update('template_artists', artist_id, data)
        
        if not result:
            return jsonify({'error': 'Artiste non trouvé'}), 404
        
        # Logger l'action 'updated'
        log_artist_action(
            artist_id,
            'updated',
            performed_by=data.get('updated_by', 'system'),
            details=f"Champs mis à jour: {', '.join(data.keys())}"
        )
        
        logger.info(f"Artiste mis à jour: {artist_id} - {result.get('name')}")
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except FileNotFoundError:
        return jsonify({'error': 'Artiste non trouvé'}), 404
    except ValueError as e:
        logger.error(f"Erreur validation mise à jour artiste {artist_id}: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Erreur mise à jour artiste {artist_id}: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


@artists_bp.route('/<int:artist_id>', methods=['DELETE'])
def delete_artist(artist_id: int):
    """
    DELETE /api/artists/:id - Suppression d'un artiste
    
    Note: Pas de JSON body pour DELETE (conformément à PostgREST)
    
    Returns:
        200: Artiste supprimé
        404: Artiste non trouvé
        500: Erreur serveur
    """
    try:
        # Suppression via client admin
        client = get_admin_client()
        success = client.delete('template_artists', artist_id)
        
        if success:
            # Logger l'action 'deleted'
            log_artist_action(
                artist_id,
                'deleted',
                performed_by=request.args.get('deleted_by', 'system'),
                details=f"Artiste {artist_id} supprimé"
            )
            
            logger.info(f"Artiste supprimé: {artist_id}")
            
            return jsonify({
                'success': True,
                'message': 'Artiste supprimé'
            }), 200
        else:
            return jsonify({'error': 'Artiste non trouvé'}), 404
        
    except FileNotFoundError:
        return jsonify({'error': 'Artiste non trouvé'}), 404
    except Exception as e:
        logger.error(f"Erreur suppression artiste {artist_id}: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


@artists_bp.route('/<int:artist_id>/approve', methods=['PATCH'])
def approve_artist(artist_id: int):
    """
    PATCH /api/artists/:id/approve - Approuver un artiste
    
    Returns:
        200: Artiste approuvé
        404: Artiste non trouvé
        500: Erreur serveur
    """
    try:
        data = {
            'status': 'approved',
            'updated_at': datetime.utcnow().isoformat()
        }
        
        client = get_admin_client()
        result = client.update('template_artists', artist_id, data)
        
        if not result:
            return jsonify({'error': 'Artiste non trouvé'}), 404
        
        # Logger l'action 'approved'
        log_artist_action(
            artist_id,
            'approved',
            performed_by=request.args.get('approved_by', 'admin'),
            details=f"Artiste {result.get('name')} approuvé"
        )
        
        logger.info(f"Artiste approuvé: {artist_id} - {result.get('name')}")
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except FileNotFoundError:
        return jsonify({'error': 'Artiste non trouvé'}), 404
    except Exception as e:
        logger.error(f"Erreur approbation artiste {artist_id}: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


@artists_bp.route('/<int:artist_id>/reject', methods=['PATCH'])
def reject_artist(artist_id: int):
    """
    PATCH /api/artists/:id/reject - Rejeter un artiste
    
    Body (JSON, optionnel):
        {
            "reason": "Raison du rejet"
        }
    
    Returns:
        200: Artiste rejeté
        404: Artiste non trouvé
        500: Erreur serveur
    """
    try:
        request_data = request.get_json() or {}
        reason = request_data.get('reason', 'Non spécifié')
        
        data = {
            'status': 'rejected',
            'updated_at': datetime.utcnow().isoformat()
        }
        
        client = get_admin_client()
        result = client.update('template_artists', artist_id, data)
        
        if not result:
            return jsonify({'error': 'Artiste non trouvé'}), 404
        
        # Logger l'action 'rejected' avec raison
        log_artist_action(
            artist_id,
            'rejected',
            performed_by=request.args.get('rejected_by', 'admin'),
            details=f"Artiste {result.get('name')} rejeté. Raison: {reason}"
        )
        
        logger.info(f"Artiste rejeté: {artist_id} - {result.get('name')}")
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except FileNotFoundError:
        return jsonify({'error': 'Artiste non trouvé'}), 404
    except Exception as e:
        logger.error(f"Erreur rejet artiste {artist_id}: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


@artists_bp.route('/<int:artist_id>/actions', methods=['GET'])
def get_artist_actions(artist_id: int):
    """
    GET /api/artists/:id/actions - Historique des actions d'un artiste
    
    Query params:
        - limit: Nombre de résultats (défaut: 50)
        - offset: Offset pour pagination (défaut: 0)
    
    Returns:
        200: Liste des actions triées par action_date DESC
        500: Erreur serveur
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Validation
        if limit < 1 or limit > 200:
            return jsonify({'error': 'limit doit être entre 1 et 200'}), 400
        if offset < 0:
            return jsonify({'error': 'offset doit être >= 0'}), 400
        
        # Récupération via client public
        client = get_public_client()
        results = client.select(
            'artworks_artist_actions',
            columns='*',
            filters={'artist_id': artist_id},
            order='action_date.desc',
            limit=limit,
            offset=offset
        )
        
        logger.info(f"Historique actions artiste {artist_id}: {len(results)} résultats")
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results),
            'limit': limit,
            'offset': offset
        }), 200
        
    except ValueError as e:
        logger.error(f"Erreur validation paramètres actions artiste {artist_id}: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Erreur historique actions artiste {artist_id}: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500
