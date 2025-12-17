# 🚀 Multi-Tenant Migration - Deployment Instructions

## ⚠️ IMPORTANT - READ THIS FIRST

**The production database is missing the `tenant_id` column in several tables, causing application errors.**

The application code has been updated to use multi-tenant isolation with `tenant_id`, but the database schema hasn't been migrated yet.

## 📋 What This Migration Does

This migration adds the `tenant_id` column to all relevant tables for multi-tenant data isolation:

### Tables to be updated:
- `users`
- `paintings`
- `orders`
- `order_items`
- `cart_items`
- `carts` ← **This is causing the current errors**
- `favorites`
- `notifications`
- `exhibitions`
- `custom_requests`
- `settings`
- `stripe_events`
- `saas_sites`

### What happens:
1. Creates a `tenants` table (if it doesn't exist)
2. Creates a default tenant with `id=1` (for existing data)
3. Adds `tenant_id` column to all tables (with default value of 1)
4. All existing data is automatically associated with tenant_id=1
5. Creates performance indexes on `tenant_id` columns

## 🔧 How to Run the Migration

### Option 1: Using Scalingo CLI (Recommended for Production)

```bash
# 1. Connect to your Scalingo app
scalingo --region osc-fr1 --app preview-colin-cayre login

# 2. Run the migration script
scalingo --region osc-fr1 --app preview-colin-cayre run python migrate_add_tenant_id.py

# 3. Verify the migration succeeded
scalingo --region osc-fr1 --app preview-colin-cayre run python check_db_schema.py
```

### Option 2: Using Scalingo Web Console

1. Go to https://dashboard.scalingo.com/
2. Select your app: `preview-colin-cayre`
3. Go to "Run" tab
4. Execute command: `python migrate_add_tenant_id.py`
5. Wait for completion (should take 5-30 seconds depending on data volume)
6. Check logs for success message

### Option 3: Direct Database Access (Advanced)

If you have direct access to the PostgreSQL database:

```bash
# 1. Set the database URL
export SUPABASE_DB_URL="postgresql://user:password@host:port/database"

# 2. Run the migration locally (connects to remote DB)
python migrate_add_tenant_id.py

# 3. Verify
python check_db_schema.py
```

## ✅ Expected Output

The migration script will show:

```
============================================================
MIGRATION: Adding tenant_id columns for multi-tenant isolation
============================================================

1. Création table 'tenants'...
   ✅ Table 'tenants' créée ou vérifiée

2. Création tenant par défaut (id=1)...
   ✅ Tenant par défaut créé

3. Ajout colonne tenant_id aux tables existantes...
   ✅ Colonne tenant_id ajoutée à 'users'
   ✅ Colonne tenant_id ajoutée à 'paintings'
   ✅ Colonne tenant_id ajoutée à 'carts'
   ... (etc)

4. Création des indexes de performance pour tenant_id...
   ✅ Index 'idx_carts_tenant_id' créé sur carts(tenant_id)
   ... (etc)

============================================================
✅ MIGRATION TERMINÉE
============================================================
```

## 🔍 How to Verify the Migration

After running the migration, verify it worked:

```bash
# Check that tenant_id column exists in carts table
scalingo --region osc-fr1 --app preview-colin-cayre run python -c "
from database import get_db_connection
with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute('SELECT tenant_id FROM carts LIMIT 1')
    print('✅ tenant_id column exists in carts table')
"
```

Or check via the logs when you visit the website - the errors should disappear:
- Before: `psycopg.errors.UndefinedColumn: column "tenant_id" does not exist`
- After: No errors, pages load correctly

## 🔄 Safe to Run Multiple Times

The migration script is **idempotent** - it can be run multiple times safely:
- If tables already have `tenant_id`, they are skipped
- If indexes already exist, they are skipped
- No data is deleted or modified

## 📝 What Changed in the Code

The following code changes were made in `app.py` to properly use `tenant_id`:

1. **Line 1519**: Added `tenant_id` filter to cart lookup in `api_login_preview()`
2. **Line 1527**: Added `tenant_id` to cart INSERT in `api_login_preview()`
3. **Line 1575**: Added `tenant_id` filter to cart lookup in `login()`
4. **Line 1585**: Added `tenant_id` to cart INSERT in `login()`

These changes ensure that:
- User carts are properly isolated by tenant
- New carts are created with the correct tenant_id
- Cart lookups only return data from the current tenant

## ⚡ After Migration

Once the migration is complete:

1. **Restart the application** (optional, but recommended):
   ```bash
   scalingo --region osc-fr1 --app preview-colin-cayre restart
   ```

2. **Test the affected endpoints**:
   - Visit `/saas/launch/success` (was failing before)
   - Visit `/` (home page, was failing before)
   - Try logging in
   - Add items to cart

3. **Monitor the logs** for any remaining errors:
   ```bash
   scalingo --region osc-fr1 --app preview-colin-cayre logs --lines 100
   ```

## 🆘 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'dotenv'"

The migration script tries to load `.env` but it's not available in Scalingo. This is fine - the script will use environment variables directly. Ignore this error if you see it.

### Error: "DATABASE_URL non définie"

Make sure `SUPABASE_DB_URL` or `DATABASE_URL` is set in your Scalingo environment variables:
```bash
scalingo --region osc-fr1 --app preview-colin-cayre env-set SUPABASE_DB_URL="postgresql://..."
```

### Error: "relation 'tenants' already exists"

This is normal if the tenants table already exists. The migration will skip it and continue.

### Migration runs but errors persist

Check that you're looking at the correct app/environment. Run:
```bash
scalingo --region osc-fr1 --app preview-colin-cayre env | grep DATABASE_URL
```

## 📌 Dashboard Changes

**Question from the issue**: "dois je modifier des chose sur Dashboard (admin.artworksdigital.fr) ?"

**Answer**: No changes needed on the Dashboard side for this migration. This is purely a Template database schema change. The Dashboard doesn't directly interact with the Template's database tables.

However, after this migration:
- Each Template site can potentially have its own tenant_id
- The Dashboard continues to work as before
- No API changes are required

## 🔐 Security Note

This migration adds multi-tenant isolation to improve data security:
- Each tenant's data is isolated by `tenant_id`
- Users cannot access data from other tenants
- All database queries are filtered by tenant
- Performance is maintained with proper indexes

---

**Status**: Ready for deployment
**Risk Level**: Low (idempotent, no data loss, backward compatible with default tenant_id=1)
**Estimated Duration**: 10-60 seconds depending on data volume
