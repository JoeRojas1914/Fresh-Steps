from db import get_connection

def obtener_negocios():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id_negocio, nombre
            FROM negocio
            ORDER BY nombre
        """)
        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()