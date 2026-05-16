from datetime import datetime, timedelta
from db import get_db
from config import MAX_INTENTOS_LOGIN, BLOQUEO_MIN_LOGIN


def obtener_usuario_por_username(username):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT *
            FROM usuario
            WHERE usuario = %s AND activo = 1
        """, (username,))
        return cursor.fetchone()


def obtener_usuario_caja_activo():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT *
            FROM usuario
            WHERE rol = 'caja' AND activo = 1
            LIMIT 1
        """)
        return cursor.fetchone()


def obtener_usuarios_caja_activos():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT *
            FROM usuario
            WHERE rol = 'caja' AND activo = 1
        """)
        return cursor.fetchall()


def registrar_login_log(usuario, metodo, exito, ip, id_usuario=None, user_agent=None):
    with get_db() as (_, cursor):
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
        """, (id_usuario, usuario, metodo, int(bool(exito)), ip, user_agent))


def obtener_intentos(usuario, ip):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT *
            FROM login_intentos
            WHERE usuario=%s AND ip=%s
        """, (usuario, ip))
        return cursor.fetchone()


def registrar_fallo(usuario, ip, max_intentos=MAX_INTENTOS_LOGIN, bloqueo_min=BLOQUEO_MIN_LOGIN):
    with get_db() as (_, cursor):
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


def limpiar_intentos(usuario, ip):
    with get_db() as (_, cursor):
        cursor.execute("""
            DELETE FROM login_intentos
            WHERE usuario=%s AND ip=%s
        """, (usuario, ip))
