
import os
import psycopg2

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
	raise RuntimeError("DATABASE_URL n'est pas défini.")
conn = psycopg2.connect(DATABASE_URL)
c = conn.cursor()

# Supprimer toutes les entrées de la table paintings
c.execute("DELETE FROM paintings")
conn.commit()
conn.close()
print("Toutes les peintures ont été supprimées !")
