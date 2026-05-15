import datetime
import json
from db import get_connection
from utils import to_json_safe


def crear_servicio(id_negocio, nombre, precio, id_usuario):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            INSERT INTO servicio (id_negocio, nombre, precio)
            VALUES (%s, %s, %s)
        """, (id_negocio, nombre, precio))

        id_servicio = cursor.lastrowid

        despues = {
            "nombre": nombre,
            "precio": precio
        }

        registrar_historial(cursor, id_servicio, "CREADO", id_usuario, None, despues)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def actualizar_servicio(id_servicio, id_negocio, nombre, precio, id_usuario):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM servicio WHERE id_servicio=%s", (id_servicio,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE servicio
            SET id_negocio=%s, nombre=%s, precio=%s
            WHERE id_servicio=%s
        """, (id_negocio, nombre, precio, id_servicio))

        despues = {
            "nombre": nombre,
            "precio": precio
        }

        registrar_historial(cursor, id_servicio, "EDITADO", id_usuario, antes, despues)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def eliminar_servicio(id_servicio, id_usuario):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM articulo_servicio
            WHERE id_servicio=%s
        """, (id_servicio,))

        if cursor.fetchone()["total"] > 0:
            return False

        cursor.execute("SELECT * FROM servicio WHERE id_servicio=%s", (id_servicio,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE servicio
            SET activo = 0
            WHERE id_servicio=%s
        """, (id_servicio,))

        registrar_historial(
            cursor,
            id_servicio,
            "ELIMINADO",
            id_usuario,
            antes,
            None
        )

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()





def obtener_servicio_por_id(id_servicio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        cursor.execute("""
            SELECT s.id_servicio,
                   s.id_negocio,
                   n.nombre AS negocio,
                   s.nombre,
                   s.precio
            FROM servicio s
            JOIN Negocio n ON s.id_negocio = n.id_negocio
            WHERE s.id_servicio = %s
              AND s.activo = 1
        """, (id_servicio,))

        servicio = cursor.fetchone()
        return servicio
    finally:
        cursor.close()
        conn.close()


def contar_servicios(id_negocio=None, q=None, incluir_eliminados=False):

    conn = get_connection()
    cursor = conn.cursor()
    try:

        sql = "SELECT COUNT(*) FROM servicio WHERE 1=1"
        params = []

        if id_negocio:
            sql += " AND id_negocio = %s"
            params.append(id_negocio)

        if q:
            sql += " AND nombre LIKE %s"
            params.append(f"%{q}%")

        if not incluir_eliminados:
            sql += " AND activo = 1"

        cursor.execute(sql, params)
        total = cursor.fetchone()[0]

        return total
    finally:
        cursor.close()
        conn.close()



def obtener_servicios(id_negocio=None, q=None, incluir_eliminados=False, limit=10, offset=0):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        sql = """
            SELECT s.id_servicio,
                s.nombre,
                s.precio,
                s.id_negocio,
                s.activo,
                n.nombre AS negocio
            FROM servicio s
            JOIN negocio n ON n.id_negocio = s.id_negocio
            WHERE 1=1
        """
        params = []

        if id_negocio:
            sql += " AND s.id_negocio = %s"
            params.append(id_negocio)

        if q:
            sql += " AND s.nombre LIKE %s"
            params.append(f"%{q}%")

        if not incluir_eliminados:
            sql += " AND s.activo = 1"

        sql += " ORDER BY s.nombre ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        servicios = cursor.fetchall()

        return servicios
    finally:
        cursor.close()
        conn.close()

def servicio_tiene_ventas(cursor, id_servicio):

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM articulo_servicio
        WHERE id_servicio = %s
    """, (id_servicio,))

    row = cursor.fetchone()

    if isinstance(row, dict):
        return row["total"] > 0
    else:
        return row[0] > 0







def registrar_historial(cursor, id_servicio, accion, id_usuario, antes=None, despues=None):
    cursor.execute("""
        INSERT INTO servicios_historial
        (id_servicio, accion, id_usuario, datos_antes, datos_despues)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        id_servicio,
        accion,
        id_usuario,
        json.dumps(to_json_safe(antes)) if antes else None,
        json.dumps(to_json_safe(despues)) if despues else None
    ))

def obtener_historial_servicio(id_servicio):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        cursor.execute("""
            SELECT h.*, u.usuario AS usuario
            FROM servicios_historial h
            JOIN usuario u ON u.id_usuario = h.id_usuario
            WHERE id_servicio=%s
            ORDER BY fecha DESC
        """, (id_servicio,))

        data = cursor.fetchall()

        return data
    finally:
        cursor.close()
        conn.close()


def restaurar_servicio(id_servicio, id_usuario):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM servicio WHERE id_servicio=%s", (id_servicio,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE servicio
            SET activo = 1
            WHERE id_servicio=%s
        """, (id_servicio,))

        registrar_historial(
            cursor,
            id_servicio,
            "RESTAURADO",
            id_usuario,
            antes,
            None
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()