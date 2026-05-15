"""
Tests para services/auth_service.py — login por contraseña y por PIN.
Se usa app.test_request_context() porque el servicio llama a request.headers.
"""
from werkzeug.security import generate_password_hash
from services.auth_service import login_password_service, login_pin_service

IP = "127.0.0.1"


def test_login_password_correcto(app, usuario_admin):
    with app.test_request_context("/"):
        resultado = login_password_service(
            usuario_admin["usuario"],
            usuario_admin["password"],
            IP,
        )
    assert resultado is not None
    assert resultado != "LOCKED"
    assert resultado["usuario"] == usuario_admin["usuario"]


def test_login_password_incorrecto(app, usuario_admin):
    with app.test_request_context("/"):
        resultado = login_password_service(
            usuario_admin["usuario"],
            "contraseña_incorrecta",
            IP,
        )
    assert resultado is None


def test_login_usuario_inexistente(app):
    with app.test_request_context("/"):
        resultado = login_password_service("usuario_que_no_existe_xyz", "pass", IP)
    assert resultado is None


def test_login_pin_correcto(app, usuario_caja):
    with app.test_request_context("/"):
        resultado = login_pin_service(usuario_caja["pin"], IP)
    assert resultado is not None
    assert resultado != "LOCKED"
    assert resultado["usuario"] == usuario_caja["usuario"]


def test_login_pin_incorrecto(app, usuario_caja):
    with app.test_request_context("/"):
        resultado = login_pin_service("0000", IP)
    assert resultado is None or resultado == "LOCKED"


def test_lockout_despues_de_intentos_fallidos(app, db_conn, usuario_admin):
    """Después de 5 intentos fallidos, el siguiente intento retorna LOCKED."""
    IP_LOCKOUT = "10.99.99.1"
    username = usuario_admin["usuario"]

    with app.test_request_context("/"):
        for _ in range(5):
            login_password_service(username, "pass_incorrecta", IP_LOCKOUT)
        resultado = login_password_service(username, "pass_incorrecta", IP_LOCKOUT)

    assert resultado == "LOCKED"

    cursor = db_conn.cursor()
    cursor.execute(
        "DELETE FROM login_intentos WHERE usuario = %s AND ip = %s", (username, IP_LOCKOUT)
    )
    cursor.execute(
        "DELETE FROM login_log WHERE usuario = %s AND ip = %s", (username, IP_LOCKOUT)
    )
    db_conn.commit()
    cursor.close()


def test_usuario_inactivo_no_puede_hacer_login(app, db_conn):
    """Un usuario con activo=0 no puede autenticarse."""
    username = "test_inactivo_pytest"
    password = "TestPass123!"

    cursor = db_conn.cursor()
    cursor.execute(
        """INSERT INTO usuario (usuario, password_hash, rol, nombre, activo)
           VALUES (%s, %s, 'caja', 'Inactivo Test', 0)""",
        (username, generate_password_hash(password)),
    )
    db_conn.commit()
    uid = cursor.lastrowid
    cursor.close()

    with app.test_request_context("/"):
        resultado = login_password_service(username, password, IP)

    assert resultado is None

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM login_log      WHERE id_usuario = %s", (uid,))
    cursor.execute("DELETE FROM login_intentos WHERE usuario    = %s", (username,))
    cursor.execute("DELETE FROM usuario        WHERE id_usuario = %s", (uid,))
    db_conn.commit()
    cursor.close()
