"""
Module de gestion Supabase REST API (PostgREST)
Fournit une interface fiable pour les opérations CRUD sur les artistes
"""

import os
import requests
import time
import logging
from typing import Dict, List, Optional, Any
from functools import wraps

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('supabase_client')

# Configuration Supabase REST API
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')

if not SUPABASE_URL:
    logger.warning("⚠️ SUPABASE_URL non définie - Les opérations REST API échoueront")
if not SUPABASE_ANON_KEY:
    logger.warning("⚠️ SUPABASE_ANON_KEY non définie - Les lectures publiques échoueront")
if not SUPABASE_SERVICE_KEY:
    logger.warning("⚠️ SUPABASE_SERVICE_KEY non définie - Les opérations admin échoueront")

# Colonnes valides pour chaque table (centralisé pour éviter erreurs PGRST204/PGRST205)
VALID_COLUMNS = {
    'template_artists': [
        'id', 'name', 'email', 'phone', 'bio', 'website', 
        'price', 'status', 'created_at', 'updated_at'
    ],
    'artworks_artist_actions': [
        'id', 'artist_id', 'action', 'action_date', 
        'performed_by', 'details', 'created_at'
    ],
    'paintings': [
        'id', 'name', 'image', 'price', 'quantity', 'create_date',
        'description', 'description_long', 'dimensions', 'technique',
        'year', 'category', 'status', 'image_2', 'image_3', 'image_4',
        'weight', 'framed', 'certificate', 'unique_piece', 'display_order'
    ]
}

# Timeout par défaut pour les requêtes (en secondes)
DEFAULT_TIMEOUT = 10

# Configuration retry exponentiel
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2  # 1s, 2s, 4s


def retry_on_network_error(max_retries=MAX_RETRIES):
    """
    Décorateur pour retry exponentiel sur erreurs réseau
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = RETRY_BACKOFF_FACTOR ** attempt
                        logger.warning(
                            f"Tentative {attempt + 1}/{max_retries} échouée pour {func.__name__}: {e}. "
                            f"Nouvelle tentative dans {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"Toutes les tentatives ({max_retries}) ont échoué pour {func.__name__}: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator


def validate_columns(table_name: str, columns: List[str]) -> List[str]:
    """
    Valide que les colonnes existent pour une table donnée
    Évite les erreurs PGRST204/PGRST205
    
    Args:
        table_name: Nom de la table
        columns: Liste des colonnes à valider
    
    Returns:
        Liste des colonnes valides uniquement
    """
    if table_name not in VALID_COLUMNS:
        logger.warning(f"Table {table_name} inconnue - validation colonnes impossible")
        return columns
    
    valid = VALID_COLUMNS[table_name]
    validated = [col for col in columns if col in valid]
    invalid = [col for col in columns if col not in valid]
    
    if invalid:
        logger.warning(
            f"Colonnes invalides ignorées pour {table_name}: {invalid}. "
            f"Colonnes valides: {valid}"
        )
    
    return validated


def clean_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nettoie les données en retirant les champs None
    
    Args:
        data: Dictionnaire de données
    
    Returns:
        Dictionnaire nettoyé (sans None)
    """
    return {k: v for k, v in data.items() if v is not None}


class SupabaseClient:
    """
    Client Supabase REST API avec gestion complète des erreurs et retry
    """
    
    def __init__(self, use_service_key: bool = False):
        """
        Initialise le client Supabase
        
        Args:
            use_service_key: Si True, utilise SERVICE_KEY (opérations admin)
                           Si False, utilise ANON_KEY (lectures publiques)
        """
        self.base_url = SUPABASE_URL
        self.api_key = SUPABASE_SERVICE_KEY if use_service_key else SUPABASE_ANON_KEY
        self.use_service_key = use_service_key
        
        if not self.base_url:
            raise ValueError("SUPABASE_URL non définie")
        if not self.api_key:
            key_type = "SERVICE_KEY" if use_service_key else "ANON_KEY"
            raise ValueError(f"SUPABASE_{key_type} non définie")
        
        logger.info(
            f"SupabaseClient initialisé avec {'SERVICE_KEY' if use_service_key else 'ANON_KEY'}"
        )
    
    def _get_headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        """
        Construit les headers requis pour l'API Supabase
        
        Args:
            prefer: Header Prefer optionnel (ex: "return=representation")
        
        Returns:
            Dictionnaire des headers
        """
        headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        if prefer:
            headers['Prefer'] = prefer
        
        return headers
    
    def _handle_response(self, response: requests.Response, operation: str) -> Any:
        """
        Gère la réponse de l'API Supabase avec logging détaillé
        
        Args:
            response: Réponse requests
            operation: Description de l'opération (pour logging)
        
        Returns:
            Données JSON de la réponse
        
        Raises:
            ValueError: Pour les erreurs 400 (Bad Request)
            FileNotFoundError: Pour les erreurs 404 (Not Found)
            RuntimeError: Pour les autres erreurs
        """
        logger.info(
            f"Supabase {operation}: {response.status_code} "
            f"({response.elapsed.total_seconds():.3f}s)"
        )
        
        if response.status_code == 200 or response.status_code == 201:
            return response.json() if response.text else []
        
        # Gestion erreurs PostgREST
        error_body = response.text
        try:
            error_json = response.json()
            error_message = error_json.get('message', error_body)
            error_code = error_json.get('code', '')
        except:
            error_message = error_body
            error_code = ''
        
        if response.status_code == 400:
            logger.error(f"400 Bad Request - {operation}: {error_message}")
            raise ValueError(f"Payload invalide: {error_message}")
        
        elif response.status_code == 404:
            logger.error(f"404 Not Found - {operation}: {error_message}")
            raise FileNotFoundError(f"Ressource non trouvée: {error_message}")
        
        elif error_code == 'PGRST204':
            logger.error(f"PGRST204 - Colonne inexistante: {error_message}")
            raise ValueError(f"Colonne inexistante: {error_message}")
        
        elif error_code == 'PGRST205':
            logger.error(f"PGRST205 - Table inexistante: {error_message}")
            raise ValueError(f"Table inexistante: {error_message}")
        
        else:
            logger.error(
                f"Erreur Supabase {response.status_code} - {operation}: {error_message}"
            )
            raise RuntimeError(f"Erreur API: {response.status_code} - {error_message}")
    
    @retry_on_network_error()
    def select(
        self, 
        table: str, 
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        SELECT avec filtres, tri et pagination
        
        Args:
            table: Nom de la table
            columns: Colonnes à sélectionner (défaut: "*")
            filters: Filtres WHERE (ex: {"status": "approved"})
            order: Tri (ex: "created_at.desc")
            limit: Limite de résultats
            offset: Offset pour pagination
        
        Returns:
            Liste de dictionnaires (résultats)
        """
        url = f"{self.base_url}/rest/v1/{table}"
        params = {'select': columns}
        
        if filters:
            for key, value in filters.items():
                params[key] = f"eq.{value}"
        
        if order:
            params['order'] = order
        
        if limit is not None:
            params['limit'] = limit
        
        if offset is not None:
            params['offset'] = offset
        
        logger.debug(f"SELECT {table}: {params}")
        
        response = requests.get(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=DEFAULT_TIMEOUT
        )
        
        return self._handle_response(response, f"SELECT {table}")
    
    @retry_on_network_error()
    def insert(
        self, 
        table: str, 
        data: Dict[str, Any],
        return_representation: bool = True
    ) -> Dict[str, Any]:
        """
        INSERT avec retour complet de l'enregistrement créé
        
        Args:
            table: Nom de la table
            data: Données à insérer
            return_representation: Si True, retourne l'enregistrement créé complet
        
        Returns:
            Enregistrement créé (si return_representation=True)
        """
        # Nettoyer les données (retirer None)
        cleaned_data = clean_data(data)
        
        url = f"{self.base_url}/rest/v1/{table}"
        prefer = "return=representation" if return_representation else None
        
        logger.debug(f"INSERT {table}: {cleaned_data}")
        
        response = requests.post(
            url,
            headers=self._get_headers(prefer=prefer),
            json=cleaned_data,
            timeout=DEFAULT_TIMEOUT
        )
        
        result = self._handle_response(response, f"INSERT {table}")
        return result[0] if result else {}
    
    @retry_on_network_error()
    def update(
        self,
        table: str,
        record_id: int,
        data: Dict[str, Any],
        return_representation: bool = True
    ) -> Dict[str, Any]:
        """
        UPDATE par ID avec retour complet
        
        Args:
            table: Nom de la table
            record_id: ID de l'enregistrement
            data: Données à mettre à jour
            return_representation: Si True, retourne l'enregistrement mis à jour complet
        
        Returns:
            Enregistrement mis à jour
        """
        # Nettoyer les données
        cleaned_data = clean_data(data)
        
        url = f"{self.base_url}/rest/v1/{table}"
        params = {'id': f'eq.{record_id}'}
        prefer = "return=representation" if return_representation else None
        
        logger.debug(f"UPDATE {table} id={record_id}: {cleaned_data}")
        
        response = requests.patch(
            url,
            headers=self._get_headers(prefer=prefer),
            params=params,
            json=cleaned_data,
            timeout=DEFAULT_TIMEOUT
        )
        
        result = self._handle_response(response, f"UPDATE {table} id={record_id}")
        return result[0] if result else {}
    
    @retry_on_network_error()
    def delete(self, table: str, record_id: int) -> bool:
        """
        DELETE par ID (pas de JSON body)
        
        Args:
            table: Nom de la table
            record_id: ID de l'enregistrement à supprimer
        
        Returns:
            True si suppression réussie
        """
        url = f"{self.base_url}/rest/v1/{table}"
        params = {'id': f'eq.{record_id}'}
        
        logger.debug(f"DELETE {table} id={record_id}")
        
        response = requests.delete(
            url,
            headers=self._get_headers(),
            params=params,
            timeout=DEFAULT_TIMEOUT
        )
        
        # DELETE retourne 204 No Content en cas de succès
        if response.status_code == 204:
            logger.info(f"DELETE {table} id={record_id}: Success")
            return True
        elif response.status_code == 404:
            logger.warning(f"DELETE {table} id={record_id}: Not Found")
            raise FileNotFoundError(f"Enregistrement {record_id} non trouvé")
        else:
            self._handle_response(response, f"DELETE {table} id={record_id}")
            return False


# Instances globales (singleton pattern)
_public_client = None
_admin_client = None


def get_public_client() -> SupabaseClient:
    """
    Retourne le client public (ANON_KEY) pour lectures
    """
    global _public_client
    if _public_client is None:
        _public_client = SupabaseClient(use_service_key=False)
    return _public_client


def get_admin_client() -> SupabaseClient:
    """
    Retourne le client admin (SERVICE_KEY) pour opérations admin
    ATTENTION: Ne jamais exposer au navigateur!
    """
    global _admin_client
    if _admin_client is None:
        _admin_client = SupabaseClient(use_service_key=True)
    return _admin_client
