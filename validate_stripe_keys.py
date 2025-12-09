#!/usr/bin/env python3
"""
validate_stripe_keys.py

Utility script to validate Stripe key formats before propagation.
This helps catch format errors early before attempting to push keys to sites.

Usage:
  python validate_stripe_keys.py --secret-key sk_test_...
  python validate_stripe_keys.py --publishable-key pk_test_...
  python validate_stripe_keys.py --both sk_test_... pk_test_...
  
  # Or use environment variables
  export STRIPE_SECRET_KEY="sk_test_..."
  export STRIPE_PUBLISHABLE_KEY="pk_test_..."
  python validate_stripe_keys.py --env
"""

import argparse
import re
import os
import sys


def mask_key(key):
    """Mask a key for safe display in output."""
    if not key or len(key) < 10:
        return '***'
    return key[:12] + '...' + key[-4:]


def validate_secret_key(key, verbose=True):
    """
    Validate a Stripe secret key format.
    
    Args:
        key: The secret key to validate
        verbose: If True, print detailed output
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not key:
        if verbose:
            print("❌ Secret key is empty or None")
        return False
    
    if not isinstance(key, str):
        if verbose:
            print(f"❌ Secret key must be a string, got {type(key)}")
        return False
    
    # Check format: sk_(test|live)_[alphanumeric]
    pattern = r'^sk_(test|live)_[A-Za-z0-9]+$'
    if not re.match(pattern, key):
        if verbose:
            print(f"❌ Invalid secret key format: {mask_key(key)}")
            print(f"   Expected format: sk_test_... or sk_live_...")
        return False
    
    # Check length
    if len(key) < 32:
        if verbose:
            print(f"⚠️  Warning: Secret key seems short ({len(key)} chars)")
            print(f"   Stripe keys are typically 32+ characters")
            print(f"   Key: {mask_key(key)}")
        # Don't fail, just warn
    
    # Determine environment
    env = 'test' if key.startswith('sk_test_') else 'live'
    
    if verbose:
        print(f"✅ Valid secret key format")
        print(f"   Environment: {env}")
        print(f"   Length: {len(key)} characters")
        print(f"   Key: {mask_key(key)}")
    
    return True


def validate_publishable_key(key, verbose=True):
    """
    Validate a Stripe publishable key format.
    
    Args:
        key: The publishable key to validate
        verbose: If True, print detailed output
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not key:
        if verbose:
            print("❌ Publishable key is empty or None")
        return False
    
    if not isinstance(key, str):
        if verbose:
            print(f"❌ Publishable key must be a string, got {type(key)}")
        return False
    
    # Check format: pk_(test|live)_[alphanumeric]
    pattern = r'^pk_(test|live)_[A-Za-z0-9]+$'
    if not re.match(pattern, key):
        if verbose:
            print(f"❌ Invalid publishable key format: {mask_key(key)}")
            print(f"   Expected format: pk_test_... or pk_live_...")
        return False
    
    # Check length
    if len(key) < 32:
        if verbose:
            print(f"⚠️  Warning: Publishable key seems short ({len(key)} chars)")
            print(f"   Stripe keys are typically 32+ characters")
            print(f"   Key: {mask_key(key)}")
        # Don't fail, just warn
    
    # Determine environment
    env = 'test' if key.startswith('pk_test_') else 'live'
    
    if verbose:
        print(f"✅ Valid publishable key format")
        print(f"   Environment: {env}")
        print(f"   Length: {len(key)} characters")
        print(f"   Key: {mask_key(key)}")
    
    return True


def check_environment_match(secret_key, publishable_key, verbose=True):
    """
    Check if secret and publishable keys are from the same environment.
    
    Args:
        secret_key: The secret key
        publishable_key: The publishable key
        verbose: If True, print output
    
    Returns:
        bool: True if they match, False otherwise
    """
    if not secret_key or not publishable_key:
        return True  # Can't check if one is missing
    
    secret_env = 'test' if 'test' in secret_key else 'live'
    pub_env = 'test' if 'test' in publishable_key else 'live'
    
    if secret_env != pub_env:
        if verbose:
            print(f"⚠️  WARNING: Environment mismatch!")
            print(f"   Secret key is for: {secret_env}")
            print(f"   Publishable key is for: {pub_env}")
            print(f"   This is usually a mistake - use matching environments")
        return False
    
    if verbose:
        print(f"✅ Keys match environment: {secret_env}")
    
    return True


def check_whitespace(key, key_type, verbose=True):
    """
    Check for problematic whitespace in a key.
    
    Args:
        key: The key to check
        key_type: 'secret' or 'publishable'
        verbose: If True, print warnings
    
    Returns:
        bool: True if no issues, False if whitespace found
    """
    if not key:
        return True
    
    has_leading = key != key.lstrip()
    has_trailing = key != key.rstrip()
    has_internal = any(c.isspace() for c in key)
    
    if has_leading or has_trailing or has_internal:
        if verbose:
            print(f"⚠️  WARNING: Whitespace detected in {key_type} key!")
            if has_leading:
                print(f"   - Leading whitespace")
            if has_trailing:
                print(f"   - Trailing whitespace")
            if has_internal:
                print(f"   - Internal whitespace")
            print(f"   Fix: key.strip() to remove whitespace")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Validate Stripe key formats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a secret key
  python validate_stripe_keys.py --secret-key sk_test_51H...
  
  # Validate a publishable key
  python validate_stripe_keys.py --publishable-key pk_test_51H...
  
  # Validate both keys
  python validate_stripe_keys.py --both sk_test_51H... pk_test_51H...
  
  # Validate from environment variables
  export STRIPE_SECRET_KEY="sk_test_..."
  export STRIPE_PUBLISHABLE_KEY="pk_test_..."
  python validate_stripe_keys.py --env
  
  # Quiet mode (only show errors)
  python validate_stripe_keys.py --secret-key sk_test_... --quiet
        """
    )
    
    parser.add_argument('--secret-key', '--sk', dest='secret_key',
                        help='Stripe secret key to validate')
    parser.add_argument('--publishable-key', '--pk', dest='publishable_key',
                        help='Stripe publishable key to validate')
    parser.add_argument('--both', nargs=2, metavar=('SECRET_KEY', 'PUBLISHABLE_KEY'),
                        help='Validate both keys (secret first, then publishable)')
    parser.add_argument('--env', action='store_true',
                        help='Validate keys from environment variables (STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Only show errors, suppress success messages')
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    secret_key = None
    publishable_key = None
    
    # Determine which keys to validate
    if args.env:
        secret_key = os.getenv('STRIPE_SECRET_KEY')
        publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        if not secret_key and not publishable_key:
            print("❌ No keys found in environment variables")
            print("   Set STRIPE_SECRET_KEY and/or STRIPE_PUBLISHABLE_KEY")
            sys.exit(1)
    elif args.both:
        secret_key = args.both[0]
        publishable_key = args.both[1]
    else:
        secret_key = args.secret_key
        publishable_key = args.publishable_key
    
    if not secret_key and not publishable_key:
        parser.print_help()
        sys.exit(1)
    
    # Validate keys
    all_valid = True
    
    print("=" * 60)
    print("Stripe Key Validation")
    print("=" * 60)
    print()
    
    if secret_key:
        print("Validating Secret Key:")
        print("-" * 60)
        check_whitespace(secret_key, 'secret', verbose)
        if not validate_secret_key(secret_key, verbose):
            all_valid = False
        print()
    
    if publishable_key:
        print("Validating Publishable Key:")
        print("-" * 60)
        check_whitespace(publishable_key, 'publishable', verbose)
        if not validate_publishable_key(publishable_key, verbose):
            all_valid = False
        print()
    
    # Check environment match if both keys provided
    if secret_key and publishable_key:
        print("Environment Consistency Check:")
        print("-" * 60)
        if not check_environment_match(secret_key, publishable_key, verbose):
            # Don't fail, just warn
            pass
        print()
    
    # Final result
    print("=" * 60)
    if all_valid:
        print("✅ All validations passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ Validation failed - fix errors before propagating keys")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
