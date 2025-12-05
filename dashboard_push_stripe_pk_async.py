"""
dashboard_push_stripe_pk_async.py

Asynchronous version that pushes the publishable key concurrently using aiohttp.
Install requirements: pip install aiohttp

Usage:
  python dashboard_push_stripe_pk_async.py --key pk_test_... --master-key template-master-key-2025 --sites-file sites.txt

This script will run many requests concurrently with a semaphore to avoid overwhelming targets.
"""

import argparse
import asyncio
import aiohttp
import json
from urllib.parse import urljoin


async def push_one(session, site, pk, master_key, sem, timeout=10):
    api_path = '/api/export/settings/stripe_publishable_key'
    target = urljoin(site.rstrip('/') + '/', api_path.lstrip('/'))
    headers = {'Content-Type': 'application/json', 'X-API-Key': master_key}
    payload = {'value': pk}
    async with sem:
        try:
            async with session.put(target, headers=headers, json=payload, timeout=timeout) as resp:
                text = await resp.text()
                try:
                    data = await resp.json()
                except Exception:
                    data = {'status': resp.status, 'text': text}
                if resp.status == 200:
                    return site, True, data
                else:
                    return site, False, data
        except Exception as e:
            return site, False, {'error': str(e)}


async def main_async(args):
    sites = [l.strip() for l in open(args.sites_file, 'r', encoding='utf-8') if l.strip()]
    if not sites:
        print('No sites found')
        return

    sem = asyncio.Semaphore(args.concurrency)
    connector = aiohttp.TCPConnector(limit_per_host=args.concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [push_one(session, s, args.pk, args.master_key, sem) for s in sites]
        results = await asyncio.gather(*tasks)

    ok = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]

    print(f'OK: {len(ok)}, Failed: {len(failed)}')
    if failed:
        print('Failed details:')
        for site, ok, data in failed:
            print(site, data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pk', required=True, help='Publishable key to push')
    parser.add_argument('--master-key', required=True, help='Master API key for template sites')
    parser.add_argument('--sites-file', required=True, help='File with one site URL per line')
    parser.add_argument('--concurrency', type=int, default=10)
    args = parser.parse_args()
    asyncio.run(main_async(args))
