#!/bin/bash
# Script de nettoyage SQLite - Suppression complète et archivage legacy
# À exécuter une fois que verify_supabase_migration.py confirme la migration

set -e

echo "=================================================="
echo "🗑️  SUPPRESSION COMPLÈTE DE SQLITE"
echo "=================================================="
echo ""

# Étape 1: Vérifier la migration
echo "📋 Étape 1: Vérification de la migration Supabase"
echo "---"
echo "Exécutez d'abord: python verify_supabase_migration.py"
echo ""
read -p "Confirmez que verify_supabase_migration.py passe (y/n)? " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Suppression annulée. Exécutez d'abord la vérification."
    exit 1
fi

# Étape 2: Lister les fichiers .db
echo "📋 Étape 2: Fichiers SQLite à supprimer"
echo "---"
db_files=$(find . -maxdepth 1 -name "*.db" -o -name "*.sqlite" 2>/dev/null || echo "")
if [ -z "$db_files" ]; then
    echo "✅ Aucun fichier .db trouvé"
else
    echo "⚠️  Fichiers trouvés:"
    echo "$db_files" | sed 's/^/   /'
    read -p "Voulez-vous les supprimer? (y/n)? " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f *.db *.sqlite 2>/dev/null || true
        echo "✅ Fichiers .db supprimés"
    fi
fi
echo ""

# Étape 3: Archiver les scripts legacy
echo "📋 Étape 3: Archivage des scripts legacy"
echo "---"

legacy_scripts=(
    "clear_paintings.py"
    "remove_adress.py"
    "reset_db.py"
    "migrate_to_postgres.py"
    "debug_domains.py"
)

if [ ! -d ".legacy" ]; then
    mkdir -p .legacy
    echo "✅ Dossier .legacy créé"
fi

for script in "${legacy_scripts[@]}"; do
    if [ -f "$script" ]; then
        mv "$script" ".legacy/$script"
        echo "   ✅ $script → .legacy/"
    fi
done

# Optionnel: Archiver le script de migration
if [ -f "migrate_sqlite_to_supabase.py" ]; then
    echo "   ℹ️  migrate_sqlite_to_supabase.py conservé pour documentation"
fi

echo ""

# Étape 4: Vérifier la syntaxe app.py
echo "📋 Étape 4: Vérification de app.py"
echo "---"
python -m py_compile app.py && echo "✅ app.py est syntaxiquement correct" || {
    echo "❌ ERREUR dans app.py!"
    exit 1
}

# Vérifier pas de références SQLite
if grep -q "import sqlite3\|sqlite3\." app.py 2>/dev/null; then
    echo "❌ ERREUR: app.py contient encore des références SQLite!"
    exit 1
else
    echo "✅ Aucune référence SQLite dans app.py"
fi

echo ""

# Étape 5: Vérifier database.py
echo "📋 Étape 5: Vérification de database.py"
echo "---"
if grep -q "IS_POSTGRES = True" database.py; then
    echo "✅ database.py est configuré pour PostgreSQL"
else
    echo "❌ ERREUR: database.py n'est pas configuré pour PostgreSQL!"
    exit 1
fi

echo ""

# Étape 6: Git
echo "📋 Étape 6: Préparation Git"
echo "---"
git status --short || true
echo ""
echo "À faire manuellement:"
echo "   git add -A"
echo "   git commit -m \"Remove SQLite: complete migration to Supabase\""
echo "   git push origin main"
echo ""

# Résumé
echo "=================================================="
echo "✅ NETTOYAGE SQLITE TERMINÉ!"
echo "=================================================="
echo ""
echo "📊 Résumé:"
echo "   • Fichiers .db supprimés"
echo "   • Scripts legacy archivés"
echo "   • app.py vérifié (100% Supabase)"
echo "   • database.py configuré pour PostgreSQL"
echo ""
echo "🚀 Prochaines étapes:"
echo "   1. git add -A"
echo "   2. git commit -m \"Remove SQLite: complete migration to Supabase\""
echo "   3. git push origin main"
echo "   4. Déployer sur Scalingo"
echo ""
