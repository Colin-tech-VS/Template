"""
dashboard_push_stripe_sk.py

Script Python pour pousser la Stripe Secret Key (clé secrète) à un ensemble de sites templates.
⚠️ ATTENTION: Ce script manipule des clés secrètes. Utilisez-le avec précaution.

Usage:
  python dashboard_push_stripe_sk.py --secret-key sk_test_... --master-key template-master-key-2025 --sites-file sites.txt

Le fichier `sites.txt` contient une URL par ligne (ex: https://site1.example.fr).

Le script effectue un PUT vers: /api/export/settings/stripe_secret_key
Header: X-API-Key: <master-key>
Body: {"value": "sk_test_..."}

Retourne un résumé (success/failed) et logs par site.

SÉCURITÉ:
- Ne jamais logger la clé secrète complète (seulement une version masquée)
- Utiliser HTTPS uniquement pour les communications
- Stocker les clés dans des variables d'environnement ou des gestionnaires de secrets
- Limiter l'accès à ce script aux administrateurs autorisés
"""

import argparse
import json
import requests
import sys
import time
import os
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def requests_session(retries=3, backoff=0.3, status_forcelist=(500, 502, 503, 504)):
    """Crée une session requests avec retry automatique."""
    s = requests.Session()
    retries = Retry(total=retries, backoff_factor=backoff, status_forcelist=status_forcelist)
    s.mount('https://', HTTPAdapter(max_retries=retries))
    s.mount('http://', HTTPAdapter(max_retries=retries))
    return s


def load_sites_from_file(path):
    """Charge la liste des sites depuis un fichier texte (une URL par ligne)."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines()]
    return [l for l in lines if l and not l.startswith('#')]


def mask_secret_key(key):
    """Masque une clé secrète pour les logs (affiche début et fin seulement)."""
    if not key or len(key) < 10:
        return '***'
    return key[:6] + '...' + key[-4:]


def validate_secret_key(key):
    """Valide le format d'une clé secrète Stripe (sk_test_... ou sk_live_...)."""
    import re
    if not key or not isinstance(key, str):
        return False
    return bool(re.match(r'^sk_(test|live)_[A-Za-z0-9]+$', key))


def push_secret_key(site_url, secret_key, master_key, session, timeout=8):
    """
    Pousse la clé secrète Stripe vers un site template.
    
    Args:
        site_url: URL du site template
        secret_key: Clé secrète Stripe (sk_test_... ou sk_live_...)
        master_key: Clé API maître pour authentification
        session: Session requests
        timeout: Timeout en secondes
    
    Returns:
        Tuple (success: bool, response_data: dict)
    """
    api_path = '/api/export/settings/stripe_secret_key'
    target = urljoin(site_url.rstrip('/') + '/', api_path.lstrip('/'))
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': master_key
    }
    payload = {'value': secret_key}
    
    try:
        resp = session.put(target, headers=headers, json=payload, timeout=timeout)
        if resp.status_code == 200:
            return True, resp.json()
        else:
            # try to parse json error
            try:
                return False, resp.json()
            except Exception:
                return False, {'status_code': resp.status_code, 'text': resp.text}
    except Exception as e:
        return False, {'error': str(e)}


def main():
    parser = argparse.ArgumentParser(
        description='Push Stripe secret key to multiple template sites',
        epilog='⚠️  ATTENTION: Ce script manipule des clés secrètes sensibles. Utilisez avec précaution.'
    )
    parser.add_argument(
        '--secret-key', '--sk', 
        dest='sk', 
        help='Secret key to push (sk_test_... or sk_live_...). Can also use STRIPE_SECRET_KEY env var.'
    )
    parser.add_argument(
        '--master-key', 
        dest='master_key', 
        help='Master API key to authenticate to template sites. Can also use TEMPLATE_MASTER_API_KEY env var.'
    )
    parser.add_argument(
        '--sites-file', 
        dest='sites_file', 
        required=True, 
        help='File with one site URL per line'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help="Don't actually push, only show targets and validate inputs"
    )
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Skip confirmation prompt (use with caution)'
    )

    args = parser.parse_args()

    # Get secret key from args or env
    secret_key = args.sk or os.getenv('STRIPE_SECRET_KEY')
    if not secret_key:
        print('❌ Error: Secret key not provided. Use --secret-key or set STRIPE_SECRET_KEY env var.')
        sys.exit(1)

    # Validate secret key format
    if not validate_secret_key(secret_key):
        print('❌ Error: Invalid secret key format. Expected sk_test_... or sk_live_...')
        sys.exit(1)

    # Get master key from args or env
    master_key = args.master_key or os.getenv('TEMPLATE_MASTER_API_KEY')
    if not master_key:
        print('❌ Error: Master API key not provided. Use --master-key or set TEMPLATE_MASTER_API_KEY env var.')
        sys.exit(1)

    # Load sites
    sites = load_sites_from_file(args.sites_file)
    if not sites:
        print(f'❌ Error: No sites found in file {args.sites_file}')
        sys.exit(1)

    # Display summary
    masked_sk = mask_secret_key(secret_key)
    key_type = 'TEST' if secret_key.startswith('sk_test_') else 'LIVE'
    
    print('=' * 60)
    print('Stripe Secret Key Propagation')
    print('=' * 60)
    print(f'Secret key (masked): {masked_sk}')
    print(f'Key type: {key_type}')
    print(f'Target sites: {len(sites)}')
    print(f'Dry-run mode: {"YES" if args.dry_run else "NO"}')
    print('=' * 60)
    print()

    # List sites
    for i, site in enumerate(sites, 1):
        print(f'  {i}. {site}')
    print()

    # Confirmation (unless --force or --dry-run)
    if not args.dry_run and not args.force:
        print('⚠️  WARNING: You are about to push a SECRET KEY to production sites.')
        print('   This operation will replace the existing secret key on all listed sites.')
        response = input('\nType "yes" to continue: ')
        if response.lower() != 'yes':
            print('Operation cancelled.')
            sys.exit(0)
        print()

    # Execute push
    session = requests_session()
    results = []
    
    for site in sites:
        print(f'Pushing to {site} ...', end=' ')
        
        if args.dry_run:
            print('DRY-RUN (skipped)')
            results.append((site, 'dry-run', None))
            continue
        
        ok, data = push_secret_key(site, secret_key, master_key, session)
        
        if ok:
            print('✅ OK')
            results.append((site, 'ok', data))
        else:
            print('❌ FAILED')
            results.append((site, 'failed', data))
        
        # Small delay to avoid hammering
        time.sleep(0.2)

    # Summary
    print()
    print('=' * 60)
    print('Summary')
    print('=' * 60)
    
    ok_count = sum(1 for r in results if r[1] == 'ok')
    failed_count = sum(1 for r in results if r[1] == 'failed')
    dry_count = sum(1 for r in results if r[1] == 'dry-run')

    print(f'✅ Successful: {ok_count}')
    print(f'❌ Failed: {failed_count}')
    if dry_count > 0:
        print(f'🔍 Dry-run: {dry_count}')

    if failed_count > 0:
        print()
        print('Failed sites details:')
        print('-' * 60)
        for site, status, data in results:
            if status == 'failed':
                print(f'Site: {site}')
                print(f'Error: {data}')
                print()

    # Exit code
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == '__main__':
    main()
