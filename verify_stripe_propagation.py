#!/usr/bin/env python3
"""
verify_stripe_propagation.py

Utility script to verify that Stripe keys have been successfully propagated
to template sites and are working correctly.

Usage:
  python verify_stripe_propagation.py --sites-file sites.txt
  python verify_stripe_propagation.py --site https://site1.example.fr
  python verify_stripe_propagation.py --sites-file sites.txt --check-health
"""

import argparse
import json
import requests
import sys
from urllib.parse import urljoin
from datetime import datetime


def load_sites_from_file(path):
    """Load site URLs from a file."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines()]
    return [l for l in lines if l and not l.startswith('#')]


def check_publishable_key(site_url, timeout=10):
    """
    Check if a site has a valid publishable key configured.
    
    Returns:
        tuple: (success: bool, key: str, error: str)
    """
    api_path = '/api/stripe-pk'
    target = urljoin(site_url.rstrip('/') + '/', api_path.lstrip('/'))
    
    try:
        resp = requests.get(target, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success') and data.get('publishable_key'):
                return True, data['publishable_key'], None
            else:
                return False, None, 'No publishable key in response'
        else:
            return False, None, f'HTTP {resp.status_code}'
    except requests.exceptions.Timeout:
        return False, None, 'Timeout'
    except requests.exceptions.ConnectionError:
        return False, None, 'Connection refused'
    except Exception as e:
        return False, None, str(e)


def check_health(site_url, timeout=10):
    """
    Check if a site has a health check endpoint and is responding.
    
    Returns:
        tuple: (success: bool, details: dict, error: str)
    """
    api_path = '/api/health/stripe'
    target = urljoin(site_url.rstrip('/') + '/', api_path.lstrip('/'))
    
    try:
        resp = requests.get(target, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            return True, data, None
        else:
            return False, None, f'HTTP {resp.status_code}'
    except requests.exceptions.Timeout:
        return False, None, 'Timeout'
    except requests.exceptions.ConnectionError:
        return False, None, 'Connection refused'
    except Exception as e:
        return False, None, str(e)


def verify_site(site_url, check_health_endpoint=False, verbose=True):
    """
    Verify Stripe configuration on a single site.
    
    Returns:
        dict: Verification results
    """
    results = {
        'site': site_url,
        'timestamp': datetime.now().isoformat(),
        'publishable_key_ok': False,
        'publishable_key': None,
        'health_check_ok': None,
        'health_details': None,
        'errors': []
    }
    
    if verbose:
        print(f"\nVerifying: {site_url}")
        print("-" * 60)
    
    # Check publishable key
    if verbose:
        print("  Checking publishable key... ", end='', flush=True)
    
    success, key, error = check_publishable_key(site_url)
    results['publishable_key_ok'] = success
    results['publishable_key'] = key
    
    if success:
        if verbose:
            print(f"✅ OK")
            print(f"     Key: {key[:15]}..." if key else "     (empty)")
            # Determine environment
            env = 'test' if key and 'test' in key else 'live'
            print(f"     Environment: {env}")
    else:
        if verbose:
            print(f"❌ FAILED")
            print(f"     Error: {error}")
        results['errors'].append(f"Publishable key check failed: {error}")
    
    # Check health endpoint if requested
    if check_health_endpoint:
        if verbose:
            print("  Checking health endpoint... ", end='', flush=True)
        
        success, details, error = check_health(site_url)
        results['health_check_ok'] = success
        results['health_details'] = details
        
        if success:
            if verbose:
                print(f"✅ OK")
                if details:
                    print(f"     Secret key configured: {details.get('secret_key_configured', 'unknown')}")
                    print(f"     Publishable key configured: {details.get('publishable_key_configured', 'unknown')}")
                    print(f"     Environment: {details.get('environment', 'unknown')}")
        else:
            if verbose:
                print(f"⚠️  Not available")
                print(f"     Error: {error}")
            # Don't add to errors - health endpoint is optional
    
    return results


def print_summary(all_results):
    """Print a summary of all verification results."""
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    total = len(all_results)
    pk_success = sum(1 for r in all_results if r['publishable_key_ok'])
    pk_failed = total - pk_success
    
    print(f"\nTotal sites checked: {total}")
    print(f"Publishable key OK: {pk_success}")
    print(f"Publishable key FAILED: {pk_failed}")
    
    # Check health results if available
    health_checked = sum(1 for r in all_results if r['health_check_ok'] is not None)
    if health_checked > 0:
        health_success = sum(1 for r in all_results if r['health_check_ok'])
        print(f"\nHealth check available: {health_success}/{health_checked}")
    
    # List failed sites
    if pk_failed > 0:
        print("\n❌ Failed sites:")
        for r in all_results:
            if not r['publishable_key_ok']:
                print(f"  - {r['site']}")
                for error in r['errors']:
                    print(f"    {error}")
    
    # Check for environment consistency
    environments = {}
    for r in all_results:
        if r['publishable_key']:
            env = 'test' if 'test' in r['publishable_key'] else 'live'
            environments[env] = environments.get(env, 0) + 1
    
    if len(environments) > 1:
        print("\n⚠️  WARNING: Mixed environments detected!")
        for env, count in environments.items():
            print(f"  - {count} site(s) using {env} keys")
        print("  Ensure all sites are using the correct environment")
    
    print("=" * 60)
    
    return pk_failed == 0


def main():
    parser = argparse.ArgumentParser(
        description='Verify Stripe key propagation to template sites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify all sites from a file
  python verify_stripe_propagation.py --sites-file sites.txt
  
  # Verify a single site
  python verify_stripe_propagation.py --site https://site1.example.fr
  
  # Include health check endpoint
  python verify_stripe_propagation.py --sites-file sites.txt --check-health
  
  # Save results to JSON
  python verify_stripe_propagation.py --sites-file sites.txt --output results.json
  
  # Quiet mode (only show summary)
  python verify_stripe_propagation.py --sites-file sites.txt --quiet
        """
    )
    
    parser.add_argument('--sites-file', dest='sites_file',
                        help='File containing site URLs (one per line)')
    parser.add_argument('--site', dest='single_site',
                        help='Verify a single site')
    parser.add_argument('--check-health', action='store_true',
                        help='Also check the health endpoint (if available)')
    parser.add_argument('--output', '-o', dest='output_file',
                        help='Save results to a JSON file')
    parser.add_argument('--timeout', type=int, default=10,
                        help='Request timeout in seconds (default: 10)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Only show summary, not detailed output')
    
    args = parser.parse_args()
    
    # Determine sites to check
    sites = []
    if args.single_site:
        sites = [args.single_site]
    elif args.sites_file:
        sites = load_sites_from_file(args.sites_file)
    else:
        parser.print_help()
        sys.exit(1)
    
    if not sites:
        print("❌ No sites to verify")
        sys.exit(1)
    
    verbose = not args.quiet
    
    if verbose:
        print("=" * 60)
        print("Stripe Propagation Verification")
        print("=" * 60)
        print(f"\nSites to verify: {len(sites)}")
        print(f"Health check: {'enabled' if args.check_health else 'disabled'}")
        print(f"Timeout: {args.timeout}s")
    
    # Verify each site
    all_results = []
    for site in sites:
        result = verify_site(
            site,
            check_health_endpoint=args.check_health,
            verbose=verbose
        )
        all_results.append(result)
    
    # Print summary
    success = print_summary(all_results)
    
    # Save results if requested
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n💾 Results saved to: {args.output_file}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
