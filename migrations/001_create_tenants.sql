-- 001_create_tenants.sql
-- Create tenants table and add tenant_id to core tables

BEGIN;

CREATE TABLE IF NOT EXISTS tenants (
  id SERIAL PRIMARY KEY,
  host TEXT UNIQUE NOT NULL,
  name TEXT,
  stripe_pk TEXT,
  stripe_sk TEXT,
  smtp_from TEXT,
  settings_json JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Insert a default tenant (replace example.com)
INSERT INTO tenants (host, name) VALUES ('example.com', 'Default') ON CONFLICT (host) DO NOTHING;

-- Add tenant_id columns (if not present)
ALTER TABLE users   ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
ALTER TABLE paintings ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
ALTER TABLE orders  ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);
ALTER TABLE settings ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id);

-- Assign existing rows to default tenant
UPDATE users    SET tenant_id = (SELECT id FROM tenants WHERE host='example.com') WHERE tenant_id IS NULL;
UPDATE paintings SET tenant_id = (SELECT id FROM tenants WHERE host='example.com') WHERE tenant_id IS NULL;
UPDATE orders   SET tenant_id = (SELECT id FROM tenants WHERE host='example.com') WHERE tenant_id IS NULL;
UPDATE settings SET tenant_id = (SELECT id FROM tenants WHERE host='example.com') WHERE tenant_id IS NULL;

COMMIT;
