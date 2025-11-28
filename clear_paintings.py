# clear_paintings.py
import sqlite3

DB_PATH = 'paintings.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Supprimer toutes les entrées de la table paintings
c.execute("DELETE FROM paintings")

conn.commit()
conn.close()

print("Toutes les peintures ont été supprimées !")
