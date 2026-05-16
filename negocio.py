from db import get_db


def obtener_negocios():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT id_negocio, nombre
            FROM negocio
            ORDER BY nombre
        """)
        return cursor.fetchall()