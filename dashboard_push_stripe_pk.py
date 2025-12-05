"""
dashboard_push_stripe_pk.py

Simple script Python (requests) que le dashboard peut utiliser pour "pusher"
la Stripe Publishable Key à un ensemble de sites templates.

Usage:
  python dashboard_push_stripe_pk.py --key pk_test_... --master-key template-master-key-2025 --sites-file sites.txt

Le fichier `sites.txt` contient une URL par ligne (ex: https://site1.example.fr).

Le script effectue un PUT vers: /api/export/settings/stripe_publishable_key
Header: X-API-Key: <master-key>
Body: {"value": "pk_test_..."}

Retourne un résumé (success/failed) et logs par site.
"""

import argparse
import json
import requests
import sys
import time
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def requests_session(retries=3, backoff=0.3, status_forcelist=(500, 502, 503, 504)):
    s = requests.Session()
    retries = Retry(total=retries, backoff_factor=backoff, status_forcelist=status_forcelist)
    s.mount('https://', HTTPAdapter(max_retries=retries))
    s.mount('http://', HTTPAdapter(max_retries=retries))
    return s


def load_sites_from_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines()]
    return [l for l in lines if l]


def push_publishable_key(site_url, publishable_key, master_key, session, timeout=8):
    api_path = '/api/export/settings/stripe_publishable_key'
    target = urljoin(site_url.rstrip('/') + '/', api_path.lstrip('/'))
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': master_key
    }
    payload = {'value': publishable_key}
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
    parser = argparse.ArgumentParser(description='Push Stripe publishable key to multiple sites')
    parser.add_argument('--publishable-key', '--key', dest='pk', required=True, help='Publishable key to push (pk_test_...)')
    parser.add_argument('--master-key', dest='master_key', required=True, help='Master API key to authenticate to the template sites')
    parser.add_argument('--sites-file', dest='sites_file', required=True, help='File with one site URL per line')
    parser.add_argument('--dry-run', action='store_true', help="Don't actually push, only show targets")
    parser.add_argument('--concurrency', type=int, default=1, help='Serial by default. Increase for parallel (not implemented in this simple script)')

    args = parser.parse_args()

    sites = load_sites_from_file(args.sites_file)
    if not sites:
        print('No sites found in file', args.sites_file)
        sys.exit(1)

    print(f"Will push publishable key to {len(sites)} sites (dry-run={args.dry_run})")

    session = requests_session()

    results = []
    for site in sites:
        print(f"Pushing to {site} ...", end=' ')
        if args.dry_run:
            print('DRY-RUN')
            results.append((site, 'dry-run', None))
            continue
        ok, data = push_publishable_key(site, args.pk, args.master_key, session)
        if ok:
            print('OK')
            results.append((site, 'ok', data))
        else:
            print('FAILED')
            results.append((site, 'failed', data))
        # small delay to avoid hammering
        time.sleep(0.2)

    # summary
    ok_count = sum(1 for r in results if r[1] == 'ok')
    failed_count = sum(1 for r in results if r[1] == 'failed')
    dry = sum(1 for r in results if r[1] == 'dry-run')

    print('\nSummary:')
    print(f'  OK: {ok_count}')
    print(f'  Failed: {failed_count}')
    print(f'  Dry-run: {dry}')

    if failed_count > 0:
        print('\nFailed sites details:')
        for site, status, data in results:
            if status == 'failed':
                print(site, data)


if __name__ == '__main__':
    main()
