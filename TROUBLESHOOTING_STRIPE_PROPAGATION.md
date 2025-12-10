# Troubleshooting Stripe Key Propagation

This guide helps you diagnose and resolve issues when propagating Stripe keys (publishable and secret keys) from the dashboard to template sites.

## 📋 Table of Contents

1. [Quick Diagnosis](#quick-diagnosis)
2. [Common Errors](#common-errors)
3. [Step-by-Step Troubleshooting](#step-by-step-troubleshooting)
4. [Network and Connectivity Issues](#network-and-connectivity-issues)
5. [Authentication Problems](#authentication-problems)
6. [Key Format and Validation](#key-format-and-validation)
7. [Performance and Timeout Issues](#performance-and-timeout-issues)
8. [Verification and Testing](#verification-and-testing)
9. [Advanced Debugging](#advanced-debugging)
10. [Prevention and Best Practices](#prevention-and-best-practices)

---

## Quick Diagnosis

Before diving into detailed troubleshooting, run these quick checks:

### 1. Check Site Accessibility

```bash
# Test if the site is reachable
curl -I https://your-site.example.fr

# Test the specific API endpoint
curl -X GET https://your-site.example.fr/api/stripe-pk
```

### 2. Verify API Key

```bash
# Test authentication
curl -X PUT "https://your-site.example.fr/api/export/settings/stripe_publishable_key" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_MASTER_KEY" \
  -d '{"value":"pk_test_dummy"}' \
  -v
```

### 3. Test with Dry-Run

```bash
# Test the propagation script without making changes
python dashboard_push_stripe_sk.py \
  --sites-file sites.txt \
  --dry-run
```

---

## Common Errors

### Error: `invalid_api_key`

**HTTP Status:** 401 Unauthorized

**Cause:** The `TEMPLATE_MASTER_API_KEY` provided doesn't match the one configured on the template site.

**Solutions:**

1. **Verify the master key on the dashboard:**
   ```bash
   echo $TEMPLATE_MASTER_API_KEY
   ```

2. **Check the template's configuration:**
   - If using environment variables: Check the template's `.env` file or server environment
   - If using database: Check the `admin_settings` table for `template_master_api_key`

3. **Ensure no whitespace or invisible characters:**
   ```bash
   # Remove any trailing whitespace
   export TEMPLATE_MASTER_API_KEY="$(echo $TEMPLATE_MASTER_API_KEY | tr -d '[:space:]')"
   ```

4. **Test with curl to isolate the issue:**
   ```bash
   curl -X PUT "https://your-site.example.fr/api/export/settings/stripe_publishable_key" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-master-key-here" \
     -d '{"value":"pk_test_test"}' \
     -v
   ```

---

### Error: `invalid_secret_format` or `invalid_publishable_key_format`

**HTTP Status:** 400 Bad Request

**Cause:** The Stripe key doesn't match the expected format.

**Solutions:**

1. **Verify the key format:**
   - Secret keys must start with `sk_test_` or `sk_live_`
   - Publishable keys must start with `pk_test_` or `pk_live_`
   - Keys must contain only alphanumeric characters after the prefix

2. **Check for common issues:**
   ```bash
   # Check for whitespace
   echo "$STRIPE_SECRET_KEY" | od -c
   
   # Verify format with regex
   echo "$STRIPE_SECRET_KEY" | grep -E '^sk_(test|live)_[A-Za-z0-9]+$'
   ```

3. **Copy the key directly from Stripe Dashboard:**
   - Go to https://dashboard.stripe.com/apikeys
   - Click "Reveal test key" or "Reveal live key"
   - Copy the entire key (including the prefix)

4. **Validate before propagation:**
   ```python
   import re
   
   key = "sk_test_your_key_here"
   if re.match(r'^sk_(test|live)_[A-Za-z0-9]+$', key):
       print("Valid secret key format")
   else:
       print("Invalid secret key format")
   ```

---

### Error: `Connection timeout` or `ReadTimeout`

**Cause:** The template site is not responding within the timeout period.

**Solutions:**

1. **Increase the timeout value:**
   ```bash
   # For synchronous script
   python dashboard_push_stripe_sk.py \
     --sites-file sites.txt \
     --timeout 30  # Increase from default 8 seconds
   
   # For asynchronous script
   python dashboard_push_stripe_sk_async.py \
     --sites-file sites.txt \
     --timeout 30
   ```

2. **Check site health:**
   ```bash
   # Test response time
   time curl -I https://your-site.example.fr
   
   # Check if the site is under load
   curl -w "@curl-format.txt" -o /dev/null -s https://your-site.example.fr
   ```

3. **Verify network connectivity:**
   ```bash
   # Test DNS resolution
   nslookup your-site.example.fr
   
   # Test network path
   traceroute your-site.example.fr
   
   # Check for firewall issues
   telnet your-site.example.fr 443
   ```

4. **Check server resources on the template site:**
   - CPU usage
   - Memory usage
   - Database connections
   - Application server status

---

### Error: `Connection refused` or `Connection reset`

**HTTP Status:** No response / Connection error

**Cause:** The site is not accessible or the endpoint doesn't exist.

**Solutions:**

1. **Verify the URL is correct:**
   ```bash
   # Check if HTTPS is required
   curl -I http://your-site.example.fr  # Without HTTPS
   curl -I https://your-site.example.fr # With HTTPS
   ```

2. **Ensure the endpoint exists:**
   ```bash
   # Test the API endpoint
   curl -X GET https://your-site.example.fr/api/stripe-pk
   curl -X GET https://your-site.example.fr/api/health  # If health check exists
   ```

3. **Check if the site is deployed:**
   - Verify the application server is running
   - Check deployment logs
   - Ensure the correct branch/version is deployed

4. **Verify SSL/TLS certificate:**
   ```bash
   # Check certificate validity
   openssl s_client -connect your-site.example.fr:443 -servername your-site.example.fr
   
   # Test with curl (ignore certificate errors for debugging only)
   curl -k https://your-site.example.fr
   ```

---

### Error: `502 Bad Gateway` or `503 Service Unavailable`

**Cause:** The application server is down or overloaded.

**Solutions:**

1. **Check application server status:**
   ```bash
   # If using systemd
   systemctl status your-app
   
   # Check server logs
   tail -f /var/log/your-app/error.log
   ```

2. **Restart the application:**
   ```bash
   # Example for systemd
   systemctl restart your-app
   
   # Example for Docker
   docker restart your-container
   
   # Example for Scalingo (see SCALINGO_DEPLOYMENT.md)
   scalingo restart
   ```

3. **Check for deployment issues:**
   - Review recent deployments
   - Check for configuration errors
   - Verify environment variables are set

4. **Propagate during off-peak hours:**
   - Schedule propagation when traffic is low
   - Use the async script with controlled concurrency

---

## Step-by-Step Troubleshooting

### Step 1: Verify Your Environment

```bash
# Check environment variables
echo "Master Key: ${TEMPLATE_MASTER_API_KEY:0:10}..." # Show only first 10 chars
echo "Secret Key: ${STRIPE_SECRET_KEY:0:10}..."
echo "Publishable Key: ${STRIPE_PUBLISHABLE_KEY:0:10}..."

# Verify Python version
python --version  # Should be 3.7+

# Check required packages
pip list | grep -E "requests|aiohttp"
```

### Step 2: Test a Single Site

Before propagating to multiple sites, test with one site:

```bash
# Create a test file with one site
echo "https://test-site.example.fr" > test-site.txt

# Run with dry-run first
python dashboard_push_stripe_sk.py \
  --sites-file test-site.txt \
  --dry-run

# Then run for real
python dashboard_push_stripe_sk.py \
  --sites-file test-site.txt
```

### Step 3: Check the Response

```bash
# Immediately verify the key was saved
curl -X GET https://test-site.example.fr/api/stripe-pk

# Expected response:
# {
#   "success": true,
#   "publishable_key": "pk_test_..."
# }
```

### Step 4: Test Stripe Integration

```bash
# On the template site, test a Stripe operation
# This ensures the key is not only saved but also functional

# Example: Create a checkout session (requires secret key)
curl -X POST https://test-site.example.fr/api/test-stripe \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

### Step 5: Propagate to All Sites

Once confirmed working on one site:

```bash
# Use the async version for multiple sites
python dashboard_push_stripe_sk_async.py \
  --sites-file sites.txt \
  --concurrency 5
```

---

## Network and Connectivity Issues

### DNS Resolution Problems

```bash
# Test DNS resolution
dig your-site.example.fr
nslookup your-site.example.fr

# If DNS fails, check:
# 1. Domain is correctly configured
# 2. DNS propagation is complete (can take 24-48 hours)
# 3. Your DNS server is working
```

### Proxy and Firewall Issues

```bash
# Check if you're behind a proxy
echo $HTTP_PROXY
echo $HTTPS_PROXY

# If using a proxy, configure requests to use it:
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"

# Test connection through proxy
curl -x http://proxy.example.com:8080 https://your-site.example.fr
```

### SSL Certificate Issues

```bash
# Verify certificate chain
openssl s_client -connect your-site.example.fr:443 -showcerts

# Check certificate expiration
echo | openssl s_client -servername your-site.example.fr -connect your-site.example.fr:443 2>/dev/null | openssl x509 -noout -dates

# For development only (NOT for production):
# You can temporarily disable SSL verification in the script
# But this should NEVER be done in production
```

---

## Authentication Problems

### Master API Key Mismatch

**Diagnostic Steps:**

1. **On the Dashboard:**
   ```bash
   # Check what key you're sending
   python -c "import os; print(os.getenv('TEMPLATE_MASTER_API_KEY'))"
   ```

2. **On the Template Site:**
   - Check environment variables: `echo $TEMPLATE_MASTER_API_KEY`
   - Check database: `SELECT value FROM admin_settings WHERE key = 'template_master_api_key';`
   - Check the Flask app configuration

3. **Compare the keys:**
   - They must match exactly
   - Check for case sensitivity
   - Check for trailing/leading whitespace

### Rotating the Master API Key

If you need to update the master API key:

1. **Update on all template sites first:**
   ```bash
   # SSH into each template
   export TEMPLATE_MASTER_API_KEY="new-master-key-2025"
   # Or update in .env file
   ```

2. **Then update on the dashboard:**
   ```bash
   export TEMPLATE_MASTER_API_KEY="new-master-key-2025"
   ```

3. **Test the propagation:**
   ```bash
   python dashboard_push_stripe_sk.py --sites-file sites.txt --dry-run
   ```

---

## Key Format and Validation

### Stripe Key Format Reference

| Key Type | Prefix | Example | Where Used |
|----------|--------|---------|------------|
| Test Secret | `sk_test_` | `sk_test_51H...` | Server-side (test) |
| Live Secret | `sk_live_` | `sk_live_51H...` | Server-side (production) |
| Test Publishable | `pk_test_` | `pk_test_51H...` | Client-side (test) |
| Live Publishable | `pk_live_` | `pk_live_51H...` | Client-side (production) |

### Validation Script

```python
#!/usr/bin/env python3
"""Validate Stripe key formats"""

import re
import sys

def validate_stripe_key(key, key_type):
    """
    Validate a Stripe key format
    
    Args:
        key: The Stripe key to validate
        key_type: 'secret' or 'publishable'
    """
    if key_type == 'secret':
        pattern = r'^sk_(test|live)_[A-Za-z0-9]+$'
        if not re.match(pattern, key):
            print(f"❌ Invalid secret key format")
            print(f"   Expected: sk_test_... or sk_live_...")
            print(f"   Got: {key[:15]}...")
            return False
    elif key_type == 'publishable':
        pattern = r'^pk_(test|live)_[A-Za-z0-9]+$'
        if not re.match(pattern, key):
            print(f"❌ Invalid publishable key format")
            print(f"   Expected: pk_test_... or pk_live_...")
            print(f"   Got: {key[:15]}...")
            return False
    
    # Check key length (Stripe keys are typically 32+ chars)
    if len(key) < 32:
        print(f"⚠️  Warning: Key seems too short ({len(key)} chars)")
        print(f"   Stripe keys are typically 32+ characters")
    
    print(f"✅ Valid {key_type} key format")
    return True

if __name__ == "__main__":
    # Example usage with clearly fake keys
    secret_key = "sk_test_EXAMPLE1234567890abcdefghijklmnopqrstuvwxyz"
    publishable_key = "pk_test_EXAMPLE1234567890abcdefghijklmnopqrstuvwxyz"
    
    validate_stripe_key(secret_key, 'secret')
    validate_stripe_key(publishable_key, 'publishable')
```

### Common Format Mistakes

1. **Whitespace in the key:**
   ```bash
   # Wrong: Key with trailing space
   export STRIPE_SECRET_KEY="sk_test_abc123 "
   
   # Correct: Trim whitespace
   export STRIPE_SECRET_KEY="$(echo 'sk_test_abc123' | tr -d '[:space:]')"
   ```

2. **Wrong key type:**
   ```bash
   # Don't use publishable key as secret key
   # Wrong: Using pk_ for secret operations
   export STRIPE_SECRET_KEY="pk_test_abc123"  # ❌
   
   # Correct: Use sk_ for secret operations
   export STRIPE_SECRET_KEY="sk_test_abc123"  # ✅
   ```

3. **Mixing test and live keys:**
   ```bash
   # Don't mix test and live environments
   # Wrong: Test secret with live publishable
   export STRIPE_SECRET_KEY="sk_test_abc123"
   export STRIPE_PUBLISHABLE_KEY="pk_live_xyz789"  # ❌
   
   # Correct: Use matching environment
   export STRIPE_SECRET_KEY="sk_test_abc123"
   export STRIPE_PUBLISHABLE_KEY="pk_test_xyz789"  # ✅
   ```

---

## Performance and Timeout Issues

### Optimizing Propagation Speed

1. **Use the Async Script for Multiple Sites:**
   ```bash
   # Synchronous (slow for many sites)
   python dashboard_push_stripe_sk.py --sites-file sites.txt
   
   # Asynchronous (fast, parallel execution)
   python dashboard_push_stripe_sk_async.py \
     --sites-file sites.txt \
     --concurrency 10
   ```

2. **Adjust Concurrency Based on Site Count:**
   ```bash
   # For 1-10 sites: Use synchronous or low concurrency
   python dashboard_push_stripe_sk_async.py --concurrency 3
   
   # For 11-50 sites: Medium concurrency
   python dashboard_push_stripe_sk_async.py --concurrency 10
   
   # For 50+ sites: High concurrency
   python dashboard_push_stripe_sk_async.py --concurrency 20
   ```

3. **Batch Large Propagations:**
   ```bash
   # Split into multiple files
   split -l 20 sites.txt sites-batch-
   
   # Process each batch
   for batch in sites-batch-*; do
     python dashboard_push_stripe_sk_async.py --sites-file $batch --concurrency 10
     sleep 5  # Small delay between batches
   done
   ```

### Handling Slow Sites

```bash
# Increase timeout for specific slow sites
python dashboard_push_stripe_sk.py \
  --sites-file slow-sites.txt \
  --timeout 30

# Or create a separate list for slow sites
echo "https://slow-site1.example.fr" > slow-sites.txt
echo "https://slow-site2.example.fr" >> slow-sites.txt
```

### Monitoring Progress

```bash
# Add verbose logging (modify script if needed)
python dashboard_push_stripe_sk.py \
  --sites-file sites.txt \
  --verbose 2>&1 | tee propagation.log

# Monitor in real-time
tail -f propagation.log
```

---

## Verification and Testing

### Post-Propagation Verification Script

```bash
#!/bin/bash
# verify_propagation.sh
# Verifies that Stripe keys were successfully propagated

SITES_FILE=$1

if [ -z "$SITES_FILE" ]; then
  echo "Usage: $0 <sites-file>"
  exit 1
fi

echo "Verifying Stripe key propagation..."
echo "=================================="

success=0
failed=0

while IFS= read -r site; do
  # Skip comments and empty lines
  [[ "$site" =~ ^#.*$ ]] && continue
  [[ -z "$site" ]] && continue
  
  echo -n "Checking $site... "
  
  response=$(curl -s -w "\n%{http_code}" "$site/api/stripe-pk" 2>/dev/null)
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)
  
  if [ "$http_code" = "200" ]; then
    pk=$(echo "$body" | grep -o '"publishable_key":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$pk" ]; then
      echo "✅ OK (${pk:0:15}...)"
      ((success++))
    else
      echo "⚠️  No key found"
      ((failed++))
    fi
  else
    echo "❌ Failed (HTTP $http_code)"
    ((failed++))
  fi
done < "$SITES_FILE"

echo "=================================="
echo "Success: $success"
echo "Failed: $failed"
echo "Total: $((success + failed))"

if [ $failed -gt 0 ]; then
  exit 1
fi
```

### Testing Stripe Functionality

After propagating keys, test that Stripe actually works:

```bash
# Test on a template site
curl -X POST https://your-site.example.fr/saas_launch_site \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "test.example.fr",
    "email": "test@example.com",
    "type": "standard"
  }'

# Should create a Stripe Checkout session
# Response should contain a checkout_url
```

### Automated Testing

```python
#!/usr/bin/env python3
"""Test Stripe integration after propagation"""

import requests
import json
import sys

def test_stripe_integration(site_url):
    """Test if Stripe is working on a site"""
    
    print(f"Testing Stripe integration on {site_url}")
    
    # 1. Test publishable key endpoint
    print("  1. Checking publishable key... ", end="")
    try:
        resp = requests.get(f"{site_url}/api/stripe-pk", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success') and data.get('publishable_key'):
                print(f"✅ OK ({data['publishable_key'][:15]}...)")
            else:
                print(f"❌ No key in response")
                return False
        else:
            print(f"❌ HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # 2. Test that the site can reach Stripe API (optional)
    # This would require a test endpoint on the template
    
    print("  ✅ All tests passed")
    return True

if __name__ == "__main__":
    sites = [
        "https://site1.example.fr",
        "https://site2.example.fr",
    ]
    
    results = []
    for site in sites:
        success = test_stripe_integration(site)
        results.append((site, success))
        print()
    
    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    
    if failed > 0:
        print("\nFailed sites:")
        for site, success in results:
            if not success:
                print(f"  - {site}")
        sys.exit(1)
```

---

## Advanced Debugging

### Enable Detailed Logging

Modify the propagation scripts to add detailed logging:

```python
import logging

# Add to the beginning of the script
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='stripe_propagation.log'
)

logger = logging.getLogger(__name__)
```

### Network Debugging with Charles Proxy or mitmproxy

```bash
# Install mitmproxy
pip install mitmproxy

# Run mitmproxy
mitmproxy -p 8080

# Configure the script to use the proxy
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080

# Run the propagation script
python dashboard_push_stripe_sk.py --sites-file sites.txt
```

### Testing with curl verbose mode

```bash
# Use -v for verbose output
curl -v -X PUT "https://your-site.example.fr/api/export/settings/stripe_secret_key" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-master-key" \
  -d '{"value":"sk_test_dummy"}'

# Save full request/response to file
curl -v -X PUT "https://your-site.example.fr/api/export/settings/stripe_secret_key" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-master-key" \
  -d '{"value":"sk_test_dummy"}' \
  2>&1 | tee curl_debug.log
```

### Inspect Template Site Logs

On the template site, check application logs:

```bash
# Flask development server logs
tail -f /var/log/flask/app.log

# Gunicorn logs
tail -f /var/log/gunicorn/error.log

# Nginx logs
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# System logs
journalctl -u your-app -f
```

### Database Inspection

Check if keys are actually saved in the database:

```sql
-- On the template site database
SELECT key, value, updated_at 
FROM admin_settings 
WHERE key IN ('stripe_secret_key', 'stripe_publishable_key', 'template_master_api_key')
ORDER BY updated_at DESC;

-- Check recent changes
SELECT key, LEFT(value, 20) as value_preview, updated_at 
FROM admin_settings 
WHERE key LIKE '%stripe%' 
ORDER BY updated_at DESC 
LIMIT 10;
```

---

## Prevention and Best Practices

### 1. Always Test with Dry-Run First

```bash
# Never skip dry-run for production
python dashboard_push_stripe_sk.py \
  --sites-file sites-production.txt \
  --dry-run

# Review the output, then run for real
python dashboard_push_stripe_sk.py \
  --sites-file sites-production.txt
```

### 2. Use Separate Files for Different Environments

```bash
# Maintain separate site lists
sites-test.txt         # Test/staging sites
sites-production.txt   # Production sites
sites-critical.txt     # High-priority sites (manual deployment)

# Use appropriate keys for each environment
export STRIPE_SECRET_KEY_TEST="sk_test_..."
export STRIPE_SECRET_KEY_LIVE="sk_live_..."
```

### 3. Implement Rollback Plan

```bash
# Before propagating new keys, backup current keys
#!/bin/bash
# backup_current_keys.sh

SITES_FILE=$1
BACKUP_FILE="keys_backup_$(date +%Y%m%d_%H%M%S).json"

echo "{" > $BACKUP_FILE
first=true

while IFS= read -r site; do
  [[ "$site" =~ ^#.*$ ]] && continue
  [[ -z "$site" ]] && continue
  
  pk=$(curl -s "$site/api/stripe-pk" | jq -r '.publishable_key')
  
  if [ "$first" = true ]; then
    first=false
  else
    echo "," >> $BACKUP_FILE
  fi
  
  echo "  \"$site\": \"$pk\"" >> $BACKUP_FILE
done < "$SITES_FILE"

echo "}" >> $BACKUP_FILE
echo "Backup saved to $BACKUP_FILE"
```

### 4. Monitor After Propagation

```bash
# Set up monitoring for Stripe errors
# Check your monitoring dashboards for:
# - Increased error rates
# - Failed payment attempts
# - API authentication errors

# Example: Query logs for Stripe errors
grep -i "stripe.*error" /var/log/app/*.log | tail -20
```

### 5. Document Your Propagations

Keep a log of when keys were propagated:

```bash
# Create a propagation log
echo "$(date -Iseconds),$(whoami),$SITES_FILE,success" >> propagation_history.csv

# Include in your automation
python dashboard_push_stripe_sk.py --sites-file sites.txt && \
  echo "$(date -Iseconds),automated,sites.txt,success" >> propagation_history.csv
```

### 6. Use Environment Variables for Secrets

Never hardcode keys in scripts:

```bash
# ❌ Bad: Hardcoded keys
python dashboard_push_stripe_sk.py --secret-key sk_test_abc123

# ✅ Good: Environment variables
export STRIPE_SECRET_KEY="sk_test_abc123"
python dashboard_push_stripe_sk.py --sites-file sites.txt

# ✅ Better: Load from secret manager
export STRIPE_SECRET_KEY=$(aws secretsmanager get-secret-value --secret-id stripe-secret-key --query SecretString --output text)
python dashboard_push_stripe_sk.py --sites-file sites.txt
```

### 7. Regular Key Rotation

```bash
# Schedule regular key rotation (e.g., every 90 days)
# 1. Generate new key in Stripe Dashboard
# 2. Test with one site
# 3. Propagate to all sites
# 4. Verify all sites work
# 5. Revoke old key in Stripe Dashboard
# 6. Document the rotation
```

### 8. Implement Health Checks

Add a health check endpoint to verify Stripe configuration:

```python
@app.route('/api/health/stripe', methods=['GET'])
def stripe_health():
    """Check if Stripe is properly configured"""
    try:
        secret_key = get_stripe_secret_key()
        publishable_key = get_stripe_publishable_key()
        
        return jsonify({
            'success': True,
            'secret_key_configured': secret_key is not None,
            'publishable_key_configured': publishable_key is not None,
            'environment': 'test' if 'test' in (secret_key or '') else 'live'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

## Related Documentation

- [Stripe Secret Key Auto-Propagation Guide](./STRIPE_SECRET_KEY_AUTO_PROPAGATION.md) - Complete guide for secret key propagation
- [Stripe Secret Key Propagation Quickstart](./STRIPE_SECRET_KEY_PROPAGATION_QUICKSTART.md) - Quick reference commands
- [Dashboard Stripe Launch Instructions](./DASHBOARD_STRIPE_LAUNCH_INSTRUCTIONS.md) - Publishable key propagation guide
- [Template Stripe Integration](./TEMPLATE_STRIPE_INTEGRATION.md) - Template-side Stripe setup
- [Scalingo Deployment](./SCALINGO_DEPLOYMENT.md) - Deployment and environment configuration

---

## Getting Help

If you've followed this troubleshooting guide and still have issues:

1. **Gather diagnostic information:**
   - Error messages and full stack traces
   - HTTP status codes and response bodies
   - Network logs (curl -v output)
   - Template site logs
   - Dashboard logs

2. **Check Stripe Dashboard:**
   - Recent API requests
   - Error logs
   - Key status (active/revoked)

3. **Verify basics:**
   - Keys are valid and active in Stripe Dashboard
   - Sites are accessible and running
   - Master API keys match on both sides
   - Network connectivity is stable

4. **Test in isolation:**
   - Test with one site only
   - Test with test keys first
   - Use dry-run mode
   - Test with curl directly

5. **Contact support:**
   - Provide all diagnostic information
   - Include relevant logs (with secrets redacted)
   - Describe what you've already tried

---

**Last updated:** December 2024  
**Version:** 1.0
