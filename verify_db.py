#!/usr/bin/env python
import sqlite3
import os

db_file = "paintings.db"
if not os.path.exists(db_file):
    print(f"Fichier {db_file} non trouve")
    exit(1)

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

print("\n" + "="*80)
print("VERIFICATION DE LA BASE DE DONNEES - Clés Stripe")
print("="*80)

cursor.execute("SELECT key, value FROM settings WHERE key LIKE 'stripe%'")
rows = cursor.fetchall()

if not rows:
    print("Aucune clé Stripe trouvée dans la base de données")
else:
    for key, value in rows:
        if len(value) > 30:
            display_value = value[:20] + "..." + value[-10:]
        else:
            display_value = value
        print(f"\n[KEY] {key}")
        print(f"[VALUE] {display_value}")
        print(f"[FULL_LENGTH] {len(value)} caractères")

conn.close()

print("\n" + "="*80)
print("Verification complete")
print("="*80)
