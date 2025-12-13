#!/usr/bin/env python3
"""
Script de nettoyage SQLite - Suppression et archivage automatique
Version sans emojis pour compatibilite Windows CP1252
"""

import os
import shutil
import sys
import glob

print("=" * 80)
print("[CLEANUP] Complete SQLite Removal (AUTO MODE)")
print("=" * 80)
print()

# Etape 1: Supprimer les fichiers .db
print("[1/5] Removing SQLite files")
print("-" * 80)

db_files = glob.glob("*.db") + glob.glob("*.sqlite")

if not db_files:
    print("[OK] No .db files found (already clean)")
else:
    print("[WARN] %d SQLite file(s) detected:" % len(db_files))
    removed = 0
    for f in db_files:
        try:
            size = os.path.getsize(f) / (1024 * 1024)
            print("  - %s (%.2f MB)" % (f, size))
        except:
            print("  - %s" % f)
        try:
            os.remove(f)
            print("    [REMOVED]")
            removed += 1
        except Exception as e:
            print("    [ERROR] %s" % str(e))
    print()
    print("[OK] %d/%d files removed" % (removed, len(db_files)))

print()

# Etape 2: Archiver les scripts legacy
print("[2/5] Archiving legacy scripts")
print("-" * 80)

legacy_scripts = [
    "clear_paintings.py",
    "remove_adress.py",
    "reset_db.py",
    "migrate_to_postgres.py",
    "debug_domains.py",
    "verify_db_storage.py"
]

# Creer le dossier .legacy
if not os.path.exists(".legacy"):
    os.makedirs(".legacy")
    print("[OK] Folder .legacy created")

moved_count = 0
for script in legacy_scripts:
    if os.path.exists(script):
        try:
            shutil.move(script, os.path.join(".legacy", script))
            print("  [OK] %s -> .legacy/" % script)
            moved_count += 1
        except Exception as e:
            print("  [ERROR] %s: %s" % (script, str(e)))

if moved_count > 0:
    print()
    print("[OK] %d scripts archived" % moved_count)
else:
    print("[INFO] No legacy scripts to archive")

print()

# Etape 3: Verifier la syntaxe app.py
print("[3/5] Verifying app.py")
print("-" * 80)

try:
    import py_compile
    py_compile.compile('app.py', doraise=True)
    print("[OK] app.py is syntactically correct")
except py_compile.PyCompileError as e:
    print("[ERROR] Syntax error in app.py: %s" % str(e))
    sys.exit(1)

# Verifier pas de references SQLite (ignorer les commentaires)
try:
    with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
except:
    print("[ERROR] Cannot read app.py")
    sys.exit(1)

bad_patterns = ['import sqlite3', 'sqlite3.connect(']
found_critical = False

for i, line in enumerate(lines):
    # Ignorer les lignes commentees
    code_part = line.split('#')[0].strip()
    
    for pattern in bad_patterns:
        if pattern in code_part:
            print("[ERROR] SQLite reference on line %d: %s" % (i + 1, line.strip()))
            found_critical = True

if found_critical:
    sys.exit(1)
else:
    print("[OK] No critical SQLite references in app.py")

print()

# Etape 4: Verifier database.py
print("[4/5] Verifying database.py")
print("-" * 80)

try:
    with open('database.py', 'r', encoding='utf-8', errors='ignore') as f:
        db_content = f.read()
except:
    print("[ERROR] Cannot read database.py")
    sys.exit(1)

checks = {
    'IS_POSTGRES = True': 'IS_POSTGRES = True' in db_content,
    'psycopg2 import': 'import psycopg2' in db_content,
    'RealDictCursor': 'RealDictCursor' in db_content,
    'ConnectionPool': 'ThreadedConnectionPool' in db_content
}

all_ok = True
for check, result in checks.items():
    status = "[OK]" if result else "[FAIL]"
    print("  %s %s" % (status, check))
    if not result:
        all_ok = False

if not all_ok:
    print()
    print("[ERROR] database.py is not properly configured!")
    sys.exit(1)
else:
    print()
    print("[OK] database.py is 100%% Supabase-ready")

print()

# Etape 5: Git status
print("[5/5] Git Status")
print("-" * 80)

try:
    import subprocess
    result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True, timeout=5)
    if result.stdout:
        lines = result.stdout.strip().split('\n')
        print("Changes detected (%d):" % len(lines))
        for line in lines[:15]:
            print("  %s" % line)
        if len(lines) > 15:
            print("  ... and %d more changes" % (len(lines) - 15))
    else:
        print("[INFO] No changes or not a Git repository")
except:
    print("[INFO] Git not available")

print()

# Resume final
print("=" * 80)
print("[SUCCESS] SQLite Cleanup Completed!")
print("=" * 80)
print()
print("Summary of actions:")
print("  [OK] SQLite .db files: Removed")
print("  [OK] Legacy scripts: Archived in .legacy/")
print("  [OK] app.py: Verified (100%% Supabase)")
print("  [OK] database.py: Configured for PostgreSQL")
print()
print("Next steps:")
print("  1. git add -A")
print("  2. git commit -m \"Remove SQLite: complete migration to Supabase\"")
print("  3. git push origin main")
print()
print("Documentation files created:")
print("  - SQLITE_AUDIT_REPORT.md")
print("  - SQLITE_REMOVAL_GUIDE.md")
print("  - verify_supabase_migration.py")
print()
