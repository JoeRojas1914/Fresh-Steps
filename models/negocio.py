from db import get_db


def obtener_negocios():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT id_negocio, nombre
            FROM negocio
            ORDER BY nombre
        """)
        return cursor.fetchall()


def cargar_tipos_por_negocio() -> dict:
    """Devuelve {id_negocio: tipo} leyendo desde la BD."""
    with get_db() as (_, cursor):
        cursor.execute("SELECT id_negocio, tipo FROM negocio WHERE tipo IS NOT NULL")
        return {row["id_negocio"]: row["tipo"] for row in cursor.fetchall()}
