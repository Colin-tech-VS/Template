"""
dashboard_push_stripe_sk_async.py

Version asynchrone du script de propagation de la Stripe Secret Key.
Utilise asyncio et aiohttp pour des performances optimales sur de nombreux sites.

⚠️ ATTENTION: Ce script manipule des clés secrètes. Utilisez-le avec précaution.

Usage:
  python dashboard_push_stripe_sk_async.py --secret-key sk_test_... --master-key template-master-key-2025 --sites-file sites.txt

Installation requise:
  pip install aiohttp

SÉCURITÉ:
- Ne jamais logger la clé secrète complète
- Utiliser HTTPS uniquement
- Stocker les clés dans des variables d'environnement ou des gestionnaires de secrets
"""

import argparse
import asyncio
import json
import sys
import os
import re
from urllib.parse import urljoin
import aiohttp


def mask_secret_key(key):
    """Masque une clé secrète pour les logs."""
    if not key or len(key) < 10:
        return '***'
    return key[:6] + '...' + key[-4:]


def validate_secret_key(key):
    """Valide le format d'une clé secrète Stripe."""
    if not key or not isinstance(key, str):
        return False
    return bool(re.match(r'^sk_(test|live)_[A-Za-z0-9]+$', key))


def load_sites_from_file(path):
    """Charge la liste des sites depuis un fichier texte."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines()]
    return [l for l in lines if l and not l.startswith('#')]


async def push_secret_key_async(session, site_url, secret_key, master_key, timeout=10):
    """
    Pousse la clé secrète vers un site de manière asynchrone.
    
    Returns:
        dict: Résultat avec 'site', 'success', et 'data' ou 'error'
    """
    api_path = '/api/export/settings/stripe_secret_key'
    target = urljoin(site_url.rstrip('/') + '/', api_path.lstrip('/'))
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': master_key
    }
    payload = {'value': secret_key}

    try:
        async with session.put(
            target, 
            headers=headers, 
            json=payload, 
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            status = resp.status
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()
            
            success = (status == 200)
            return {
                'site': site_url,
                'success': success,
                'status_code': status,
                'data': data
            }
    except asyncio.TimeoutError:
        return {
            'site': site_url,
            'success': False,
            'error': 'timeout'
        }
    except Exception as e:
        return {
            'site': site_url,
            'success': False,
            'error': str(e)
        }


async def push_to_all_sites(sites, secret_key, master_key, concurrency=5, timeout=10):
    """
    Pousse la clé secrète vers tous les sites en parallèle (avec limite de concurrence).
    
    Args:
        sites: Liste des URLs de sites
        secret_key: Clé secrète Stripe
        master_key: Clé API maître
        concurrency: Nombre de requêtes simultanées maximum
        timeout: Timeout en secondes pour chaque requête (default: 10)
    
    Returns:
        list: Liste des résultats
    """
    connector = aiohttp.TCPConnector(limit=concurrency)
    client_timeout = aiohttp.ClientTimeout(total=timeout * 3)
    
    async with aiohttp.ClientSession(connector=connector, timeout=client_timeout) as session:
        tasks = [
            push_secret_key_async(session, site, secret_key, master_key, timeout)
            for site in sites
        ]
        results = await asyncio.gather(*tasks)
        return results


def main():
    parser = argparse.ArgumentParser(
        description='Push Stripe secret key to multiple sites (async version)',
        epilog='⚠️  ATTENTION: Ce script manipule des clés secrètes sensibles.'
    )
    parser.add_argument(
        '--secret-key', '--sk',
        dest='sk',
        help='Secret key to push (sk_test_... or sk_live_...). Can also use STRIPE_SECRET_KEY env var.'
    )
    parser.add_argument(
        '--master-key',
        dest='master_key',
        help='Master API key. Can also use TEMPLATE_MASTER_API_KEY env var.'
    )
    parser.add_argument(
        '--sites-file',
        dest='sites_file',
        required=True,
        help='File with one site URL per line'
    )
    parser.add_argument(
        '--concurrency',
        type=int,
        default=5,
        help='Max concurrent requests (default: 5)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Timeout per request in seconds (default: 10)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Don't actually push, only validate"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )

    args = parser.parse_args()

    # Get secret key
    secret_key = args.sk or os.getenv('STRIPE_SECRET_KEY')
    if not secret_key:
        print('❌ Error: Secret key not provided.')
        sys.exit(1)

    # Validate secret key
    if not validate_secret_key(secret_key):
        print('❌ Error: Invalid secret key format.')
        sys.exit(1)

    # Get master key
    master_key = args.master_key or os.getenv('TEMPLATE_MASTER_API_KEY')
    if not master_key:
        print('❌ Error: Master API key not provided.')
        sys.exit(1)

    # Load sites
    sites = load_sites_from_file(args.sites_file)
    if not sites:
        print(f'❌ Error: No sites found in {args.sites_file}')
        sys.exit(1)

    # Display info
    masked_sk = mask_secret_key(secret_key)
    key_type = 'TEST' if secret_key.startswith('sk_test_') else 'LIVE'

    print('=' * 60)
    print('Stripe Secret Key Propagation (Async)')
    print('=' * 60)
    print(f'Secret key (masked): {masked_sk}')
    print(f'Key type: {key_type}')
    print(f'Target sites: {len(sites)}')
    print(f'Concurrency: {args.concurrency}')
    print(f'Dry-run: {"YES" if args.dry_run else "NO"}')
    print('=' * 60)
    print()

    # List sites
    for i, site in enumerate(sites, 1):
        print(f'  {i}. {site}')
    print()

    # Confirmation
    if not args.dry_run and not args.force:
        print('⚠️  WARNING: You are about to push a SECRET KEY to production sites.')
        response = input('\nType "yes" to continue: ')
        if response.lower() != 'yes':
            print('Operation cancelled.')
            sys.exit(0)
        print()

    # Dry-run exit
    if args.dry_run:
        print('DRY-RUN mode: No actual push performed.')
        print('All validations passed. Ready to execute.')
        sys.exit(0)

    # Execute async push
    print('Starting propagation...\n')
    results = asyncio.run(push_to_all_sites(sites, secret_key, master_key, args.concurrency, args.timeout))

    # Display results
    print()
    print('=' * 60)
    print('Results')
    print('=' * 60)

    success_count = 0
    failed_count = 0

    for result in results:
        site = result['site']
        if result['success']:
            print(f'✅ {site} - OK')
            success_count += 1
        else:
            error = result.get('error') or result.get('data', 'Unknown error')
            print(f'❌ {site} - FAILED: {error}')
            failed_count += 1

    # Summary
    print()
    print('=' * 60)
    print('Summary')
    print('=' * 60)
    print(f'✅ Successful: {success_count}')
    print(f'❌ Failed: {failed_count}')

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == '__main__':
    main()
