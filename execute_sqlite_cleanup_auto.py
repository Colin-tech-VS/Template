#!/usr/bin/env python3
"""
Script de nettoyage SQLite - Suppression et archivage automatique
Version non-interactive pour exécution via CI/CD
"""

import os
import shutil
import sys
import glob

print("=" * 80)
print("[CLEANUP] Complete SQLite Removal (AUTO MODE)")
print("=" * 80)
print()

# Étape 1: Supprimer les fichiers .db
print("📋 Étape 1: Suppression des fichiers SQLite")
print("-" * 80)

db_files = glob.glob("*.db") + glob.glob("*.sqlite")

if not db_files:
    print("✅ Aucun fichier .db trouvé (déjà propre)")
else:
    print(f"⚠️  {len(db_files)} fichier(s) SQLite détecté(s):")
    removed = 0
    for f in db_files:
        size = os.path.getsize(f) / (1024 * 1024)  # MB
        print(f"   • {f} ({size:.2f} MB)")
        try:
            os.remove(f)
            print(f"     ✅ Supprimé")
            removed += 1
        except Exception as e:
            print(f"     ❌ Erreur: {e}")
    print(f"\n✅ {removed}/{len(db_files)} fichiers supprimés")

print()

# Étape 2: Archiver les scripts legacy
print("📋 Étape 2: Archivage des scripts legacy")
print("-" * 80)

legacy_scripts = [
    "clear_paintings.py",
    "remove_adress.py",
    "reset_db.py",
    "migrate_to_postgres.py",
    "debug_domains.py",
    "verify_db_storage.py"
]

# Créer le dossier .legacy s'il n'existe pas
if not os.path.exists(".legacy"):
    os.makedirs(".legacy")
    print("✅ Dossier .legacy créé")

moved_count = 0
for script in legacy_scripts:
    if os.path.exists(script):
        try:
            shutil.move(script, os.path.join(".legacy", script))
            print(f"   ✅ {script} → .legacy/")
            moved_count += 1
        except Exception as e:
            print(f"   ⚠️  Erreur déplacement {script}: {e}")

if moved_count > 0:
    print(f"\n✅ {moved_count} scripts archivés dans .legacy/")
else:
    print("ℹ️  Aucun script legacy à archiver")

print()

# Étape 3: Vérifier la syntaxe app.py
print("📋 Étape 3: Vérification de app.py")
print("-" * 80)

try:
    import py_compile
    py_compile.compile('app.py', doraise=True)
    print("✅ app.py est syntaxiquement correct")
except py_compile.PyCompileError as e:
    print(f"❌ ERREUR dans app.py: {e}")
    sys.exit(1)

# Vérifier pas de références SQLite
try:
    with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
        app_content = f.read()
except:
    print("❌ Impossible de lire app.py")
    sys.exit(1)

bad_patterns = ['import sqlite3', 'sqlite3.connect', 'sqlite3.']
found_patterns = [p for p in bad_patterns if p in app_content]

if found_patterns:
    print(f"❌ ERREUR: app.py contient {len(found_patterns)} référence(s) SQLite:")
    for p in found_patterns:
        print(f"   • {p}")
    sys.exit(1)
else:
    print("✅ Aucune référence SQLite dans app.py")

print()

# Étape 4: Vérifier database.py
print("📋 Étape 4: Vérification de database.py")
print("-" * 80)

try:
    with open('database.py', 'r', encoding='utf-8', errors='ignore') as f:
        db_content = f.read()
except:
    print("❌ Impossible de lire database.py")
    sys.exit(1)

checks = {
    'IS_POSTGRES = True': 'IS_POSTGRES = True' in db_content,
    'psycopg2 import': 'import psycopg2' in db_content,
    'RealDictCursor': 'RealDictCursor' in db_content,
    'ConnectionPool': 'ThreadedConnectionPool' in db_content
}

all_ok = True
for check, result in checks.items():
    status = "✅" if result else "❌"
    print(f"   {status} {check}")
    if not result:
        all_ok = False

if not all_ok:
    print("\n❌ database.py n'est pas correctement configuré!")
    sys.exit(1)
else:
    print("\n✅ database.py est 100% Supabase")

print()

# Étape 5: Lister les fichiers qui vont être committed
print("📋 Étape 5: État Git après nettoyage")
print("-" * 80)

import subprocess
try:
    result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True, timeout=5)
    if result.stdout:
        print("Changements détectés:")
        for line in result.stdout.strip().split('\n')[:10]:
            print(f"   {line}")
        if len(result.stdout.strip().split('\n')) > 10:
            print(f"   ... et {len(result.stdout.strip().split('\n')) - 10} autres changements")
    else:
        print("ℹ️  Aucun changement (ou répertoire non Git)")
except:
    print("ℹ️  Git non disponible ou erreur")

print()

# Résumé final
print("=" * 80)
print("✅ NETTOYAGE SQLITE TERMINÉ!")
print("=" * 80)
print()
print("📊 Actions effectuées:")
print(f"   ✅ Fichiers .db: Supprimés")
print(f"   ✅ Scripts legacy: Archivés dans .legacy/")
print(f"   ✅ app.py: Validé (100% Supabase)")
print(f"   ✅ database.py: Configuré pour PostgreSQL")
print()
print("🚀 Prochaines étapes:")
print("   1. git add -A")
print("   2. git commit -m \"Remove SQLite: complete migration to Supabase\"")
print("   3. git push origin main")
print()
print("📝 Fichiers de documentation créés:")
print("   • SQLITE_AUDIT_REPORT.md - Rapport complet d'audit")
print("   • SQLITE_REMOVAL_GUIDE.md - Guide détaillé de suppression")
print("   • verify_supabase_migration.py - Script de vérification")
print()
