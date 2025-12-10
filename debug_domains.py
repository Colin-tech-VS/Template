#!/usr/bin/env python
import sqlite3

try:
    conn = sqlite3.connect('paintings.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Chercher les domaines enregistrés
    c.execute("SELECT key, value FROM settings WHERE key LIKE '%domain%' OR key LIKE '%site_url%' OR key LIKE '%final_domain%'")
    domains = c.fetchall()
    
    print("=== Domaines enregistrés ===")
    for row in domains:
        if row:
            print(f"{row['key']}: {row['value']}")
    
    # Chercher les sites SAAS
    if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='saas_sites'").fetchone():
        c.execute("SELECT user_id, status, final_domain FROM saas_sites LIMIT 5")
        print("\n=== Sites SAAS ===")
        for row in c.fetchall():
            if row:
                print(f"User {row['user_id']}: {row['final_domain']} ({row['status']})")
    
    conn.close()
except Exception as e:
    print(f"Erreur: {e}")
    import traceback
    traceback.print_exc()
