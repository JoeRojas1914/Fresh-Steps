from db import get_connection
import json


def obtener_usuarios(q=None, rol=None, activo=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        sql = """
            SELECT id_usuario, usuario, nombre, apellido,
                   telefono, correo, cp, rol, activo, creado_en
            FROM usuario
            WHERE 1=1
        """
        params = []

        if q:
            sql += " AND (usuario LIKE %s OR nombre LIKE %s OR apellido LIKE %s OR telefono LIKE %s)"
            like = f"%{q}%"
            params += [like, like, like, like]

        if rol:
            sql += " AND rol = %s"
            params.append(rol)

        if activo is not None:
            sql += " AND activo = %s"
            params.append(activo)

        sql += " ORDER BY creado_en DESC"
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def obtener_usuario_por_id(id_usuario):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM usuario
            WHERE id_usuario = %s
        """, (id_usuario,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def crear_usuario(usuario_nombre, password_hash, rol, pin_hash,
                  nombre=None, apellido=None, telefono=None,
                  correo=None, cp=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO usuario
                (usuario, password_hash, rol, pin_hash,
                 nombre, apellido, telefono, correo, cp)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (usuario_nombre, password_hash, rol, pin_hash,
              nombre, apellido, telefono, correo, cp))
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def actualizar_usuario(id_usuario, usuario_nombre, rol,
                       nombre=None, apellido=None, telefono=None,
                       correo=None, cp=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE usuario
            SET usuario=%s, rol=%s,
                nombre=%s, apellido=%s,
                telefono=%s, correo=%s, cp=%s
            WHERE id_usuario=%s
        """, (usuario_nombre, rol,
              nombre, apellido, telefono, correo, cp,
              id_usuario))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def actualizar_password(id_usuario, password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE usuario SET password_hash=%s WHERE id_usuario=%s
        """, (password_hash, id_usuario))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def toggle_activo(id_usuario):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE usuario SET activo = NOT activo WHERE id_usuario=%s
        """, (id_usuario,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def registrar_historial_usuario(id_usuario, accion, antes, despues, admin):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO historial_usuario
            (id_usuario, accion, datos_antes, datos_despues, usuario_admin)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            id_usuario, accion,
            json.dumps(antes, default=str) if antes else None,
            json.dumps(despues, default=str) if despues else None,
            admin
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def actualizar_pin(id_usuario, pin_hash):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE usuario SET pin_hash=%s WHERE id_usuario=%s
        """, (pin_hash, id_usuario))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def obtener_historial_usuario(id_usuario):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT * FROM historial_usuario
            WHERE id_usuario=%s
            ORDER BY fecha DESC
        """, (id_usuario,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()