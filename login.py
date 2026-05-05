from datetime import datetime, timedelta
from db import get_connection


def obtener_usuario_por_username(username):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        cursor.execute("""
            SELECT *
            FROM usuario
            WHERE usuario = %s AND activo = 1
        """, (username,))

        usuario = cursor.fetchone()

        return usuario
    finally:
        cursor.close()
        conn.close()


def obtener_usuario_caja_activo():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        cursor.execute("""
            SELECT *
            FROM usuario
            WHERE rol = 'caja' AND activo = 1
            LIMIT 1
        """)

        usuario = cursor.fetchone()

        return usuario
    finally:
        cursor.close()
        conn.close()


def registrar_login_log(
    usuario,
    metodo,
    exito,
    ip,
    id_usuario=None,
    user_agent=None
):
    conn = get_connection()
    cursor = conn.cursor()
    try:

        cursor.execute("""
            INSERT INTO login_log (
                id_usuario,
                usuario,
                metodo,
                exito,
                ip,
                user_agent
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            id_usuario,
            usuario,
            metodo,
            int(bool(exito)), 
            ip,
            user_agent
        ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def obtener_intentos(usuario, ip):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        cursor.execute("""
            SELECT *
            FROM login_intentos
            WHERE usuario=%s AND ip=%s
        """, (usuario, ip))

        row = cursor.fetchone()


        return row
    finally:
        cursor.close()
        conn.close()



def registrar_fallo(usuario, ip, max_intentos=5, bloqueo_min=10):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:

        # 🔥 MISMA CONEXIÓN
        cursor.execute("""
            SELECT *
            FROM login_intentos
            WHERE usuario=%s AND ip=%s
        """, (usuario, ip))

        row = cursor.fetchone()

        if not row:

            cursor.execute("""
                INSERT INTO login_intentos (usuario, ip, intentos)
                VALUES (%s,%s,1)
            """, (usuario, ip))

        else:
            intentos = row["intentos"] + 1

            if intentos >= max_intentos:

                bloqueo = datetime.now() + timedelta(minutes=bloqueo_min)

                cursor.execute("""
                    UPDATE login_intentos
                    SET intentos=%s, bloqueado_hasta=%s
                    WHERE usuario=%s AND ip=%s
                """, (intentos, bloqueo, usuario, ip))

            else:
                cursor.execute("""
                    UPDATE login_intentos
                    SET intentos=%s
                    WHERE usuario=%s AND ip=%s
                """, (intentos, usuario, ip))

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()



def limpiar_intentos(usuario, ip):

    conn = get_connection()
    cursor = conn.cursor()
    try:

        cursor.execute("""
            DELETE FROM login_intentos
            WHERE usuario=%s AND ip=%s
        """, (usuario, ip))

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()