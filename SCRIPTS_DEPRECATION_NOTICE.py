"""
Scripts SQLite Obsolètes
========================

Les scripts suivants sont obsolètes car ils dépendent de SQLite.
L'application utilise maintenant exclusivement Supabase/PostgreSQL.

Scripts Obsolètes:
------------------
- remove_adress.py
- clear_paintings.py
- verify_db_storage.py
- debug_domains.py (si dépend de SQLite)

Scripts Mis à Jour:
-------------------
✅ check_db_schema.py - Fonctionne avec Supabase
✅ reset_db.py - Fonctionne avec Supabase
✅ verify_db.py - Fonctionne avec Supabase

Nouveaux Scripts:
-----------------
✅ migrate_sqlite_to_supabase.py - Migration des données
✅ test_supabase_migration.py - Tests de validation

Utilisation:
------------

Pour vérifier la base de données:
  python verify_db.py

Pour vérifier le schéma:
  python check_db_schema.py

Pour réinitialiser (⚠️ SUPPRIME TOUT):
  python reset_db.py

Pour migrer depuis SQLite:
  python migrate_sqlite_to_supabase.py

Pour tester la migration:
  python test_supabase_migration.py

Documentation:
--------------
Voir SUPABASE_MIGRATION_GUIDE.md pour plus de détails.
"""

print(__doc__)
