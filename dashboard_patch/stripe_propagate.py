"""
Blueprint for the dashboard to propagate Stripe publishable key to template sites.
Drop this file into your dashboard Flask project and register the blueprint.

Usage:
  from dashboard_patch.stripe_propagate import bp as stripe_propagate_bp
  app.register_blueprint(stripe_propagate_bp)

Security: protect the endpoint with your dashboard's admin auth (current_user.is_admin or similar)
"""
from flask import Blueprint, request, jsonify, current_app
import threading
import time
import requests
from urllib.parse import urljoin

bp = Blueprint('stripe_propagate', __name__)

# Read from secure config / environment in real deployment
TEMPLATE_MASTER_API_KEY = current_app.config.get('TEMPLATE_MASTER_API_KEY') if 'current_app' in globals() else 'template-master-key-2025'


def push_to_site(site_url, publishable_key, master_key, timeout=8):
    api_path = '/api/export/settings/stripe_publishable_key'
    target = urljoin(site_url.rstrip('/') + '/', api_path.lstrip('/'))
    headers = {'Content-Type': 'application/json', 'X-API-Key': master_key}
    try:
        resp = requests.put(target, headers=headers, json={'value': publishable_key}, timeout=timeout)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        return {'site': site_url, 'status': resp.status_code, 'body': body}
    except Exception as e:
        return {'site': site_url, 'status': None, 'error': str(e)}


def worker_push_publishable(sites, publishable_key, master_key, results, throttle=0.2):
    for s in sites:
        results.append(push_to_site(s, publishable_key, master_key))
        time.sleep(throttle)


@bp.route('/admin/stripe/propagate', methods=['POST'])
def propagate_stripe_key():
    # SECURITY: integrate with your dashboard auth (example uses a placeholder)
    # Replace the check below with your real admin verification (Flask-Login, etc.)
    try:
        from flask_login import current_user
        if not (hasattr(current_user, 'is_authenticated') and current_user.is_authenticated and getattr(current_user, 'is_admin', False)):
            return jsonify({'success': False, 'error': 'forbidden'}), 403
    except Exception:
        # If the dashboard uses a different auth mechanism, ensure you protect this endpoint properly
        pass

    body = request.get_json() or {}
    publishable = body.get('publishable_key')
    if not publishable:
        return jsonify({'success': False, 'error': 'missing_publishable_key'}), 400

    # Retrieve sites list from your dashboard DB
    # Replace this block with your ORM or DB access
    sites = []
    try:
        # Example: if you have SQLAlchemy and a Site model
        # from models import Site
        # sites = [s.url for s in Site.query.filter_by(active=True).all()]
        # For now try a rudimentary config value
        cfg_sites = current_app.config.get('TEMPLATE_SITES_LIST')
        if cfg_sites:
            sites = list(cfg_sites)
    except Exception:
        pass

    if not sites:
        return jsonify({'success': False, 'error': 'no_sites_configured'}), 400

    # results container (will be filled by worker)
    results = []
    thread = threading.Thread(target=worker_push_publishable, args=(sites, publishable, TEMPLATE_MASTER_API_KEY, results))
    thread.daemon = True
    thread.start()

    return jsonify({'success': True, 'message': f'Propagation started to {len(sites)} sites'}), 202


@bp.route('/admin/stripe/propagation-status', methods=['GET'])
def propagation_status():
    # OPTIONAL: implement status tracking (store in DB or a cache) to review results
    return jsonify({'success': True, 'message': 'Not implemented: check logs or storage for results'})
