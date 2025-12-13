# 🗑️ Guide de Suppression Complète de SQLite

## État Actuel du Projet

Le projet Template a été **partiellement migré** vers Supabase:

✅ **Déjà complète:**
- `database.py` est configuré pour PostgreSQL/Supabase
- `app.py` utilise `get_db()` de `database.py` (pas d'imports SQLite directs)
- Code principal compatible Supabase (RealDictCursor, ON CONFLICT, etc.)

⚠️ **Résidus SQLite à nettoyer:**
- Fichiers `.db` locaux (`paintings.db`, `app.db`)
- Scripts d'administration qui référencent les vieux `.db`
- Dépendances légacy dans les scripts utilitaires

---

## Audit des Références SQLite

### Fichiers contenant des références SQLite:

```
clear_paintings.py        → Utilise paintings.db
debug_domains.py          → Utilise app.db
remove_adress.py          → Utilise app.db
verify_db_storage.py      → Référence SQLite
migrate_sqlite_to_supabase.py → Script de migration
reset_db.py              → Utilise app.db
migrate_to_postgres.py   → Migration legacy
```

### Fichiers propres (✅):

```
app.py                    → Utilise get_db() (Supabase)
database.py              → PostgreSQL/Supabase uniquement
requirements.txt         → Pas de sqlite3 (sauf legacy)
```

---

## Checklist de Suppression

### Étape 1: Vérifier la Migration Supabase

```bash
# Vérifier que toutes les données sont migrées
python verify_supabase_migration.py
```

Résultat attendu:
```
✅ Connexion Supabase: OK
✅ Tables requises: OK
✅ Contenu tables: OK
✅ Configuration: OK
```

### Étape 2: Supprimer les Fichiers .db

```bash
# Supprimer les bases SQLite
rm paintings.db
rm app.db
rm database.db (si existe)

# Vérifier la suppression
ls *.db 2>/dev/null || echo "✅ Tous les .db supprimés"
```

### Étape 3: Nettoyer les Scripts Legacy

**Option A: Supprimer complètement**
```bash
rm clear_paintings.py
rm remove_adress.py
rm reset_db.py
rm migrate_to_postgres.py
rm migrate_sqlite_to_supabase.py (si migration complète)
```

**Option B: Migrer vers Supabase (meilleure pratique)**

Réécrire les scripts pour utiliser `database.py`:

#### Exemple: clear_paintings.py → clear_paintings_supabase.py

```python
#!/usr/bin/env python3
"""Efface tous les peintures de Supabase"""

from database import get_db, adapt_query

def clear_paintings():
    """Supprime toutes les peintures"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Supprimer les articles du panier d'abord (clé étrangère)
    cursor.execute(adapt_query("DELETE FROM cart_items WHERE painting_id IN (SELECT id FROM paintings)"))
    
    # Supprimer les peintures
    cursor.execute(adapt_query("DELETE FROM paintings"))
    
    conn.commit()
    conn.close()
    
    print("✅ Toutes les peintures ont été supprimées")

if __name__ == "__main__":
    clear_paintings()
```

### Étape 4: Vérifier requirements.txt

Votre `requirements.txt` ne doit pas contenir `sqlite3` (c'est un built-in Python).

```bash
# Vérifier
grep -i sqlite requirements.txt || echo "✅ Aucune référence SQLite"
```

### Étape 5: Tester app.py

```bash
# Vérifier qu'app.py démarre sans SQLite
python -c "from app import app; print('✅ app.py charge correctement')"

# Ou lancer le serveur Flask localement
python -c "from app import app; app.run(debug=False)" &
sleep 2
curl http://localhost:5000/ 
kill %1
```

### Étape 6: Vérifier Scalingo

Si déployé sur Scalingo, vérifier que:

```bash
# 1. Variables d'environnement
scalingo -a [APP_NAME] env | grep SUPABASE_DB_URL

# 2. Logs d'application
scalingo -a [APP_NAME] logs --lines 50 | grep -i error

# 3. Test de la route
curl https://[APP_NAME].scalingo.io/api/export/settings
```

---

## Commands de Nettoyage Complet

### 1️⃣ Supprimer les fichiers SQLite

```bash
cd /path/to/Template
rm -f *.db *.sqlite
```

### 2️⃣ Archiver les scripts legacy

```bash
# Créer un dossier d'archives
mkdir -p .legacy
mv clear_paintings.py .legacy/
mv remove_adress.py .legacy/
mv reset_db.py .legacy/
mv migrate_to_postgres.py .legacy/
```

### 3️⃣ Migrer les scripts utiles

```bash
# Garder migrate_sqlite_to_supabase.py pour la documentation
# Mais le renommer
mv migrate_sqlite_to_supabase.py MIGRATION_HISTORY_migrate_sqlite_to_supabase.py
```

### 4️⃣ Vérifier la configuration

```bash
# Vérifier database.py
grep "IS_POSTGRES = True" database.py

# Vérifier app.py imports
grep "from database import" app.py
```

### 5️⃣ Commit Git

```bash
git add -A
git commit -m "Remove SQLite: delete .db files and clean up legacy scripts

- Remove: paintings.db, app.db, database.db
- Archive legacy migration scripts to .legacy/
- Verify app.py works 100% with Supabase
- No more SQLite dependencies
"
git push origin main
```

---

## Vérification Post-Suppression

### 1. Assurez-vous que app.py fonctionne

```bash
python app.py
# Vous devez voir:
# * Running on http://localhost:5000
# * Pas d'erreurs SQLite
```

### 2. Testez les endpoints critiques

```bash
# Login
curl -X POST http://localhost:5000/login \
  -d "email=test@example.com&password=test"

# Settings
curl http://localhost:5000/api/export/settings \
  -H "X-API-Key: YOUR_KEY"

# Paintings
curl http://localhost:5000/api/export/paintings \
  -H "X-API-Key: YOUR_KEY"
```

### 3. Vérifiez Supabase

Allez sur https://supabase.com et vérifiez:
- ✅ Toutes les tables existent
- ✅ Les données sont présentes
- ✅ Les performances sont bonnes

---

## Troubleshooting

### Erreur: "Table does not exist"

**Cause:** Migration Supabase incomplète

**Correction:**
```bash
python migrate_sqlite_to_supabase.py
python verify_supabase_migration.py
```

### Erreur: "KeyError: 0" ou "KeyError: 'column_name'"

**Cause:** Curseur utilise RealDictCursor mais le code accède par index

**Correction:** Vérifier que tout le code utilise `safe_row_get()`:
```python
# ❌ Mauvais
value = row[0]

# ✅ Bon
value = safe_row_get(row, 'column_name', index=0)
```

### Erreur: "Connection refused" sur Scalingo

**Cause:** SUPABASE_DB_URL pas définie

**Correction:**
```bash
scalingo -a [APP_NAME] env-set SUPABASE_DB_URL="postgresql://..."
```

---

## Après Suppression Complète

Une fois que vous avez suivi toutes les étapes:

1. ✅ app.py démarre sans erreur
2. ✅ Toutes les routes fonctionnent
3. ✅ Les données sont dans Supabase
4. ✅ Aucun fichier SQLite
5. ✅ Pas de références SQLite dans le code

**Vous pouvez maintenant:**
- ✅ Déployer en production
- ✅ Archiver les vieux backups SQLite
- ✅ Supprimer les scripts legacy
- ✅ Documenter la migration
- ✅ Célébrer! 🎉

---

## Ressources

- [Supabase Docs](https://supabase.com/docs)
- [PostgreSQL Best Practices](https://www.postgresql.org/docs/)
- [Connection Pooling](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooling)
- [MIGRATION_FINAL_REPORT.md](./MIGRATION_FINAL_REPORT.md)
- [TEMPLATE_INTEGRATION_GUIDE.md](./TEMPLATE_INTEGRATION_GUIDE.md)
