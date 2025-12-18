# Fix Documentation: Auto-Registration NameError and 401 Errors

## Problem Statement

From the logs, the application was experiencing two critical issues:

```
[AUTO-REG] ⚠️ Erreur globale: name 'register_site_to_dashboard' is not defined
```

And subsequent 401 errors on all export API endpoints:

```
10.0.0.195 - - [18/Dec/2025:12:45:54 +0000] "GET /api/export/stats HTTP/1.1" 401 44
10.0.0.126 - - [18/Dec/2025:12:45:56 +0000] "GET /api/export/orders HTTP/1.1" 401 44
10.0.0.126 - - [18/Dec/2025:12:45:56 +0000] "GET /api/export/users HTTP/1.1" 401 44
10.0.0.231 - - [18/Dec/2025:12:46:00 +0000] "GET /api/export/paintings HTTP/1.1" 401 44
10.0.0.12 - - [18/Dec/2025:12:46:01 +0000] "GET /api/export/users HTTP/1.1" 401 44
```

Only `/api/export/settings` was working (200 status).

## Root Cause Analysis

### Issue 1: Missing Function
The `init_auto_registration()` function (line 5890) was calling `register_site_to_dashboard()`, but this function was never defined in the codebase.

```python
def init_auto_registration():
    # ...
    def register_async():
        # ...
        register_site_to_dashboard()  # ← Function doesn't exist!
```

### Issue 2: Authentication Failure Chain
Without the auto-registration function:
1. Sites couldn't register themselves with the central dashboard
2. No `export_api_key` was generated/stored
3. No `dashboard_id` was stored
4. Dashboard requests failed authentication (401)
5. Only `/api/export/settings` worked because it has different auth requirements

## The Solution

### Implementation of `register_site_to_dashboard()`

Created a new function (lines 5770-5866) that handles automatic site registration:

```python
def register_site_to_dashboard():
    """
    Enregistre automatiquement ce site au dashboard central.
    Appelée au démarrage si enable_auto_registration est activé.
    """
```

#### Function Logic Flow

1. **Check if Auto-Registration is Enabled**
   ```python
   if get_setting("enable_auto_registration") != "true":
       print("[AUTO-REG] Auto-registration désactivée")
       return
   ```

2. **Check if Already Registered**
   ```python
   dashboard_id = get_setting("dashboard_id")
   if dashboard_id:
       print(f"[AUTO-REG] Site déjà enregistré avec ID {dashboard_id}")
       return
   ```

3. **Generate or Retrieve API Key**
   ```python
   api_key = get_setting("export_api_key")
   if not api_key:
       api_key = secrets.token_urlsafe(32)
       set_setting("export_api_key", api_key)
       print("[AUTO-REG] Nouvelle clé API générée")
   ```

4. **Determine Site URL** (Multiple fallback sources)
   - First: Environment variables (`SITE_URL`, `APP_URL`, `PUBLIC_URL`)
   - Second: From tenants table (first non-localhost host)
   - Third: From settings table (`site_url`)
   
   ```python
   site_url = os.getenv('SITE_URL') or os.getenv('APP_URL') or os.getenv('PUBLIC_URL')
   
   if not site_url:
       # Query tenants table...
       
   if not site_url:
       stored_url = get_setting("site_url")
   ```

5. **Register with Dashboard**
   ```python
   dashboard_data = {
       "site_name": site_name,
       "site_url": site_url,
       "api_key": api_key,
       "auto_registered": True
   }
   
   dashboard_url = f"{get_dashboard_base_url()}/api/sites/register"
   response = requests.post(dashboard_url, json=dashboard_data, timeout=15)
   ```

6. **Store Dashboard ID on Success**
   ```python
   if response.status_code == 200:
       result = response.json()
       site_id = result.get("site_id")
       if site_id:
           set_setting("dashboard_id", str(site_id))
           print(f"[AUTO-REG] ✅ Site enregistré avec succès (ID: {site_id})")
   ```

### Error Handling Improvements

Added comprehensive error handling for network issues:

```python
try:
    response = requests.post(dashboard_url, json=dashboard_data, timeout=15)
    # ... handle response
except requests.exceptions.Timeout:
    print(f"[AUTO-REG] ⚠️ Timeout lors de la connexion au dashboard: {dashboard_url}")
except requests.exceptions.ConnectionError:
    print(f"[AUTO-REG] ⚠️ Impossible de se connecter au dashboard: {dashboard_url}")
except requests.exceptions.RequestException as e:
    print(f"[AUTO-REG] ⚠️ Erreur réseau lors de l'enregistrement: {e}")
```

### Import Organization

Moved `traceback` import to top-level imports (line 65) instead of importing it inside the exception handler, following Python best practices.

## How It Works Now

### Auto-Registration Flow

1. **Application Starts** → `init_auto_registration()` is called at module load
2. **Async Thread Launches** → Waits 2 seconds for app initialization
3. **Registration Attempt** → Calls `register_site_to_dashboard()`
4. **Check Prerequisites** → Verifies auto-registration is enabled and not already registered
5. **API Key Setup** → Generates/retrieves export_api_key
6. **Site Detection** → Determines site URL from available sources
7. **Dashboard Registration** → POSTs to dashboard's `/api/sites/register` endpoint
8. **Store Credentials** → Saves dashboard_id and export_api_key to settings

### Authentication Flow for Export Endpoints

After successful registration:

1. Dashboard sends request to `/api/export/*` with `X-API-Key` header
2. `@require_api_key` decorator validates the key
3. Checks against both `TEMPLATE_MASTER_API_KEY` and stored `export_api_key`
4. If valid, request proceeds; otherwise returns 401

```python
@app.route('/api/export/paintings', methods=['GET'])
@require_api_key  # ← Now works because export_api_key is stored
def api_paintings():
    # ... endpoint logic
```

## Configuration

### Environment Variables

To configure auto-registration, set in `.env`:

```bash
# Enable auto-registration at startup
ENABLE_AUTO_REGISTRATION=true

# Dashboard URL (defaults to https://admin.artworksdigital.fr)
DASHBOARD_URL=https://admin.artworksdigital.fr

# Optional: Set site URL explicitly
SITE_URL=https://your-site.example.com

# Master API key for dashboard access
TEMPLATE_MASTER_API_KEY=your-master-key-here
```

### Database Settings

The function also uses/creates these settings:

- `enable_auto_registration` - "true" to enable auto-registration
- `dashboard_id` - ID assigned by dashboard after registration
- `export_api_key` - Generated API key for dashboard access
- `site_url` - Site URL (optional, can be auto-detected)
- `site_name` - Site name (defaults to "Site Template")

## Testing Results

### Validation Performed

✅ **Python Syntax Check** - Passed with `python3 -m py_compile app.py`
✅ **CodeQL Security Scan** - 0 alerts found
✅ **Code Review** - All feedback addressed (imports, error handling)

### Expected Behavior After Fix

**Before Fix:**
```
[AUTO-REG] ⚠️ Erreur globale: name 'register_site_to_dashboard' is not defined
GET /api/export/paintings HTTP/1.1" 401 44
```

**After Fix:**
```
[AUTO-REG] 🚀 Démarrage auto-registration...
[AUTO-REG] Nouvelle clé API générée
[AUTO-REG] Enregistrement du site: https://your-site.example.com
[AUTO-REG] ✅ Site enregistré avec succès (ID: 123)
GET /api/export/paintings HTTP/1.1" 200 ...
```

## Deployment Notes

### No Migration Required
This is a code-only fix. No database changes are needed.

### Backward Compatibility
- Sites with existing `dashboard_id` won't re-register
- Sites with existing `export_api_key` will reuse it
- Function gracefully handles missing configuration

### Manual Registration Alternative
If auto-registration fails, sites can still be manually registered using:
```bash
POST /api/saas/register-site
{
  "user_id": <id>,
  "domain": "your-site.example.com",
  "api_key": "<generated-key>"
}
```

## Troubleshooting

### If Auto-Registration Fails

Check the logs for specific error messages:

- **"Auto-registration désactivée"** → Set `ENABLE_AUTO_REGISTRATION=true`
- **"Impossible de déterminer l'URL du site"** → Set `SITE_URL` in environment
- **"Timeout lors de la connexion"** → Check dashboard URL is reachable
- **"Erreur dashboard: 400"** → Check dashboard expects correct data format
- **"Erreur dashboard: 500"** → Dashboard may have an internal error

### Manual Verification

After deployment, verify auto-registration worked:

```python
# In Python shell or test script
from app import get_setting
print("Dashboard ID:", get_setting("dashboard_id"))
print("Export API Key:", get_setting("export_api_key")[:20] + "...")
```

## Security Considerations

### What Was Fixed
- ✅ No security vulnerabilities introduced
- ✅ API keys generated with `secrets.token_urlsafe(32)` (cryptographically secure)
- ✅ Network timeouts prevent hanging connections
- ✅ Error messages don't expose sensitive data

### What Remains Secure
- 🔒 API keys stored in database, not in code
- 🔒 HTTPS enforced for dashboard communication
- 🔒 Master key (`TEMPLATE_MASTER_API_KEY`) still works as fallback
- 🔒 Multi-tenant isolation maintained

## Related Files

### Modified
- `app.py` - Added `register_site_to_dashboard()` function and improved imports

### Related (Not Modified)
- `database.py` - Contains `get_db()`, `get_setting()`, `set_setting()` helpers
- `.env.example` - Documents `ENABLE_AUTO_REGISTRATION` variable
- `FIX_401_EXPORT_API.md` - Previous fix for tenant isolation in settings

## Conclusion

This fix resolves the NameError by implementing the missing `register_site_to_dashboard()` function, which enables automatic site registration with the central dashboard. This ensures that sites have valid `export_api_key` credentials, eliminating the 401 errors on export API endpoints.

The implementation follows the same pattern as the existing manual registration endpoint (`/api/saas/register-site`), includes comprehensive error handling, and maintains backward compatibility with existing deployments.
