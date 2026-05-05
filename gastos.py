from db import get_connection
import json
from decimal import Decimal
from datetime import date, datetime



def crear_gasto(
    id_negocio,
    descripcion,
    proveedor,
    total,
    fecha_registro,
    tipo_comprobante,
    tipo_pago,
    id_usuario
):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            INSERT INTO gastos
            (id_negocio, descripcion, proveedor, total, fecha_registro,
             tipo_comprobante, tipo_pago, id_usuario)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            id_negocio,
            descripcion,
            proveedor,
            total,
            fecha_registro,
            tipo_comprobante,
            tipo_pago,
            id_usuario
        ))

        id_gasto = cursor.lastrowid

        despues = {
            "descripcion": descripcion,
            "proveedor": proveedor,
            "total": total,
            "tipo_comprobante": tipo_comprobante,
            "tipo_pago": tipo_pago
        }

        registrar_historial(cursor, id_gasto, "CREADO", id_usuario, None, despues)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()





def actualizar_gasto(
    id_gasto,
    id_negocio,
    descripcion,
    proveedor,
    total,
    fecha_registro,
    tipo_comprobante,
    tipo_pago,
    id_usuario
):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM gastos WHERE id_gasto=%s", (id_gasto,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE gastos
            SET id_negocio=%s,
                descripcion=%s,
                proveedor=%s,
                total=%s,
                fecha_registro=%s,
                tipo_comprobante=%s,
                tipo_pago=%s
            WHERE id_gasto=%s
        """, (
            id_negocio,
            descripcion,
            proveedor,
            total,
            fecha_registro,
            tipo_comprobante,
            tipo_pago,
            id_gasto
        ))

        despues = {
            "descripcion": descripcion,
            "proveedor": proveedor,
            "total": total,
            "tipo_comprobante": tipo_comprobante,
            "tipo_pago": tipo_pago
        }

        registrar_historial(cursor, id_gasto, "EDITADO", id_usuario, antes, despues)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()




def eliminar_gasto(id_gasto, id_usuario):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        cursor.execute("SELECT * FROM gastos WHERE id_gasto=%s", (id_gasto,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE gastos
            SET activo = 0
            WHERE id_gasto=%s
        """, (id_gasto,))

        registrar_historial(cursor, id_gasto, "ELIMINADO", id_usuario, antes, None)

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()




def obtener_gastos(id_negocio=None, fecha_inicio=None, fecha_fin=None, limit=10, offset=0,  incluir_eliminados=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        sql = """
            SELECT 
                g.id_gasto,
                g.id_negocio,
                n.nombre AS negocio,
                g.descripcion,
                g.proveedor,
                g.total,
                g.fecha_registro,
                g.tipo_comprobante,
                g.tipo_pago,
                u.usuario AS creado_por,
                g.activo
            FROM gastos g
            JOIN negocio n ON g.id_negocio = n.id_negocio
            JOIN usuario u ON g.id_usuario = u.id_usuario
            WHERE 1=1
        """

        params = []

        if id_negocio:
            sql += " AND g.id_negocio = %s"
            params.append(id_negocio)

        if fecha_inicio:
            sql += " AND g.fecha_registro >= %s"
            params.append(fecha_inicio)

        if fecha_fin:
            sql += " AND g.fecha_registro <= %s"
            params.append(fecha_fin)
    
        if not incluir_eliminados:
         sql += " AND g.activo = 1"


        sql += " ORDER BY g.fecha_registro DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        gastos = cursor.fetchall()

        return gastos
    finally:
        cursor.close()
        conn.close()





def obtener_gastos_por_proveedor(id_negocio, fecha_inicio, fecha_fin):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        cursor.execute("""
            SELECT proveedor, SUM(total) AS total
            FROM gastos
            WHERE id_negocio = %s
              AND fecha_registro BETWEEN %s AND %s
            GROUP BY proveedor
            ORDER BY total DESC
        """, (id_negocio, fecha_inicio, fecha_fin))

        resultados = cursor.fetchall()
        return resultados
    finally:
        cursor.close()
        conn.close()


def contar_gastos(id_negocio=None, fecha_inicio=None, fecha_fin=None, incluir_eliminados=False):
    conn = get_connection()
    cursor = conn.cursor()
    try:

        sql = "SELECT COUNT(*) FROM gastos WHERE 1=1"
        params = []

        if not incluir_eliminados:
            sql += " AND activo = 1"

        if id_negocio:
            sql += " AND id_negocio = %s"
            params.append(id_negocio)

        if fecha_inicio:
            sql += " AND fecha_registro >= %s"
            params.append(fecha_inicio)

        if fecha_fin:
            sql += " AND fecha_registro <= %s"
            params.append(fecha_fin)

        cursor.execute(sql, params)
        total = cursor.fetchone()[0]

        return total
    finally:
        cursor.close()
        conn.close()




def registrar_historial(cursor, id_gasto, accion, id_usuario, antes=None, despues=None):

    cursor.execute("""
        INSERT INTO gastos_historial
        (id_gasto, accion, id_usuario, datos_antes, datos_despues)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        id_gasto,
        accion,
        id_usuario,
        json.dumps(to_json_safe(antes)) if antes else None,
        json.dumps(to_json_safe(despues)) if despues else None
    ))




def obtener_historial_gasto(id_gasto):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        cursor.execute("""
            SELECT h.*, u.usuario AS usuario
            FROM gastos_historial h
            JOIN usuario u ON h.id_usuario = u.id_usuario
            WHERE id_gasto=%s
            ORDER BY fecha DESC
        """, (id_gasto,))

        data = cursor.fetchall()

        return data
    finally:
        cursor.close()
        conn.close()


def to_json_safe(data):
    if not data:
        return None

    safe = {}

    for k, v in data.items():
        if isinstance(v, Decimal):
            safe[k] = float(v)
        elif isinstance(v, (date, datetime)):
            safe[k] = v.isoformat()
        else:
            safe[k] = v

    return safe


def restaurar_gasto(id_gasto, id_usuario):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        cursor.execute("SELECT * FROM gastos WHERE id_gasto=%s", (id_gasto,))
        antes = cursor.fetchone()

        cursor.execute("""
            UPDATE gastos
            SET activo = 1
            WHERE id_gasto=%s
        """, (id_gasto,))

        registrar_historial(cursor, id_gasto, "RESTAURADO", id_usuario, antes, None)

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()