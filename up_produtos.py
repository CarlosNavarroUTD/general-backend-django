import csv
import psycopg2
import os

# Conexión a la base de datos (ajusta con tus variables)
conn = psycopg2.connect(
    host="localhost",   # o la IP de tu servidor si no es local
    port=5433,          # puerto mapeado en docker-compose
    dbname="flowbuilder",
    user="flowuser",
    password="flowpass"
)

cur = conn.cursor()

with open("productos-pacs.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    
    # Normalizamos los encabezados para evitar problemas con espacios o mayúsculas
    reader.fieldnames = [h.strip() for h in reader.fieldnames]

    for row in reader:
        nombre = row.get("Producto/Servicio")
        if not nombre:
            continue  # salta filas vacías

        categoria = row.get("Categoría", "").strip()
        marca = row.get("Marca", "").strip() or None
        precio = row.get("Precio", "").strip() or None
        descripcion = row.get("Descripción / Notas", "").strip() or None
        extras = row.get("Extras", "").strip() or None

        # Inserta en la tabla productos (ajusta los nombres de campos según tu modelo)
        cur.execute("""
            INSERT INTO productos_productos(nombre, descripcion, precio, categoria, extras)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (nombre) DO NOTHING
        """, (nombre, descripcion, precio, categoria, extras))

conn.commit()
cur.close()
conn.close()

print("Importación completada ✅")
