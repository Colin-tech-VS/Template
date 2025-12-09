# Quick Start: Stripe Secret Key Auto-Propagation

This guide provides a quick reference for using the Stripe secret key auto-propagation scripts. For complete documentation, see [STRIPE_SECRET_KEY_AUTO_PROPAGATION.md](./STRIPE_SECRET_KEY_AUTO_PROPAGATION.md).

## ⚠️ Security Warning

The Stripe secret key (`sk_test_...` or `sk_live_...`) is **highly sensitive**. Always:
- Use HTTPS only
- Never commit keys to Git
- Use environment variables for secrets
- Test with `sk_test_...` keys first

## Quick Commands

### 1. Test with dry-run (recommended first step)

```bash
# Using command-line arguments
python dashboard_push_stripe_sk.py \
  --secret-key sk_test_YOUR_KEY \
  --master-key YOUR_MASTER_KEY \
  --sites-file sites.txt \
  --dry-run
```

### 2. Push to sites (with environment variables - recommended)

```bash
# Set environment variables
export STRIPE_SECRET_KEY="sk_test_YOUR_KEY"
export TEMPLATE_MASTER_API_KEY="YOUR_MASTER_KEY"

# Run sync version (small number of sites)
python dashboard_push_stripe_sk.py --sites-file sites.txt

# Or run async version (many sites, faster)
python dashboard_push_stripe_sk_async.py --sites-file sites.txt --concurrency 10
```

### 3. Async version with all options

```bash
python dashboard_push_stripe_sk_async.py \
  --sites-file sites.txt \
  --concurrency 10 \
  --timeout 15 \
  --force  # Skip confirmation
```

## Files Overview

| File | Purpose |
|------|---------|
| `dashboard_push_stripe_sk.py` | Synchronous script - simple, reliable |
| `dashboard_push_stripe_sk_async.py` | Async script - fast, for many sites |
| `sites-example.txt` | Template for your sites list |
| `STRIPE_SECRET_KEY_AUTO_PROPAGATION.md` | Complete documentation |

## Create Your Sites List

1. Copy the example:
   ```bash
   cp sites-example.txt sites.txt
   ```

2. Edit `sites.txt` with your site URLs:
   ```
   https://site1.example.fr
   https://site2.example.fr
   ```

3. Keep `sites.txt` out of Git (it's already in .gitignore)

## Common Workflows

### Testing with test sites

```bash
export STRIPE_SECRET_KEY="sk_test_YOUR_TEST_KEY"
export TEMPLATE_MASTER_API_KEY="YOUR_MASTER_KEY"
python dashboard_push_stripe_sk.py --sites-file sites-test.txt --force
```

### Production deployment

```bash
export STRIPE_SECRET_KEY="sk_live_YOUR_LIVE_KEY"
export TEMPLATE_MASTER_API_KEY="YOUR_MASTER_KEY"
python dashboard_push_stripe_sk.py --sites-file sites-production.txt
# You'll be asked to confirm (no --force flag)
```

### Key rotation

```bash
# Generate new key in Stripe Dashboard, then:
export STRIPE_SECRET_KEY="sk_live_NEW_KEY"
export TEMPLATE_MASTER_API_KEY="YOUR_MASTER_KEY"
python dashboard_push_stripe_sk_async.py \
  --sites-file sites-production.txt \
  --concurrency 10 \
  --force
```

## Requirements

- Python 3.7+
- `requests` library (for sync version)
- `aiohttp` library (for async version)

```bash
pip install requests aiohttp
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| `invalid_api_key` | Check `TEMPLATE_MASTER_API_KEY` matches on template sites |
| `invalid_secret_format` | Verify key starts with `sk_test_` or `sk_live_` |
| `timeout` | Increase `--timeout` value or check site connectivity |
| `connection refused` | Verify site URL is correct and accessible |

## Get Help

```bash
# View all options
python dashboard_push_stripe_sk.py --help
python dashboard_push_stripe_sk_async.py --help
```

## Related Documentation

- Complete guide: [STRIPE_SECRET_KEY_AUTO_PROPAGATION.md](./STRIPE_SECRET_KEY_AUTO_PROPAGATION.md)
- Publishable key propagation: [TEMPLATE_STRIPE_INTEGRATION.md](./TEMPLATE_STRIPE_INTEGRATION.md)
- Stripe integration: [DASHBOARD_STRIPE_LAUNCH_INSTRUCTIONS.md](./DASHBOARD_STRIPE_LAUNCH_INSTRUCTIONS.md)

---

**Remember:** Always test with `--dry-run` first and use test keys before production deployment!
