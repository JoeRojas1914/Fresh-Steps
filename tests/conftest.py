import os
import pytest
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Carga .env.test ANTES de importar cualquier módulo que use la BD
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_base, "scripts", ".env.test"), override=True)

from app import app as flask_app  # noqa: E402  (importación deliberada post-env)
from db import get_connection      # noqa: E402


# ---------------------------------------------------------------------------
# App / cliente HTTP
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Conexión directa a BD (para setup/teardown de fixtures)
# ---------------------------------------------------------------------------

@pytest.fixture
def db_conn():
    conn = get_connection()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Usuarios de prueba
# ---------------------------------------------------------------------------

@pytest.fixture
def usuario_admin(db_conn):
    username = "test_admin_pytest"
    password = "TestPass123!"
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        """INSERT INTO usuario (usuario, password_hash, rol, nombre, activo)
           VALUES (%s, %s, 'admin', 'Admin Test', 1)""",
        (username, generate_password_hash(password)),
    )
    db_conn.commit()
    uid = cursor.lastrowid
    cursor.close()

    yield {"id_usuario": uid, "usuario": username, "password": password, "rol": "admin"}

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM historial_usuario WHERE id_usuario = %s", (uid,))
    cursor.execute("DELETE FROM login_log          WHERE id_usuario = %s", (uid,))
    cursor.execute("DELETE FROM login_intentos     WHERE usuario   = %s", (username,))
    cursor.execute("DELETE FROM usuario            WHERE id_usuario = %s", (uid,))
    db_conn.commit()
    cursor.close()


@pytest.fixture
def usuario_caja(db_conn):
    username = "test_caja_pytest"
    pin = "9876"
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        """INSERT INTO usuario (usuario, password_hash, pin_hash, rol, nombre, activo)
           VALUES (%s, %s, %s, 'caja', 'Caja Test', 1)""",
        (username, generate_password_hash("TestPass123!"), generate_password_hash(pin)),
    )
    db_conn.commit()
    uid = cursor.lastrowid
    cursor.close()

    yield {"id_usuario": uid, "usuario": username, "pin": pin, "rol": "caja"}

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM historial_usuario WHERE id_usuario = %s", (uid,))
    cursor.execute("DELETE FROM login_log         WHERE id_usuario = %s", (uid,))
    cursor.execute("DELETE FROM login_intentos WHERE usuario     = %s", (username,))
    cursor.execute("DELETE FROM usuario        WHERE id_usuario  = %s", (uid,))
    db_conn.commit()
    cursor.close()


# ---------------------------------------------------------------------------
# Cliente y servicio de prueba
# ---------------------------------------------------------------------------

@pytest.fixture
def cliente_test(db_conn, usuario_admin):
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        """INSERT INTO cliente (nombre, apellido, telefono, correo, activo, id_usuario)
           VALUES ('TestNombre', 'TestApellido', '5512345678', 'pytest@test.com', 1, %s)""",
        (usuario_admin["id_usuario"],),
    )
    db_conn.commit()
    cid = cursor.lastrowid
    cursor.close()

    yield {"id_cliente": cid, "nombre": "TestNombre", "apellido": "TestApellido"}

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM clientes_historial WHERE id_cliente = %s", (cid,))
    cursor.execute("DELETE FROM cliente           WHERE id_cliente = %s", (cid,))
    db_conn.commit()
    cursor.close()


@pytest.fixture
def servicio_calzado(db_conn):
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        "INSERT INTO servicio (id_negocio, nombre, precio, activo) VALUES (1, 'Limpieza Test', 150.00, 1)"
    )
    db_conn.commit()
    sid = cursor.lastrowid
    cursor.close()

    yield {"id_servicio": sid, "precio": 150.00}

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM servicios_historial WHERE id_servicio = %s", (sid,))
    cursor.execute("DELETE FROM servicio            WHERE id_servicio = %s", (sid,))
    db_conn.commit()
    cursor.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cleanup_venta(db_conn, id_venta):
    """Elimina todos los registros relacionados a una venta de prueba."""
    cursor = db_conn.cursor()
    cursor.execute(
        "DELETE FROM articulo_servicio WHERE id_articulo IN "
        "(SELECT id_articulo FROM articulo WHERE id_venta = %s)",
        (id_venta,),
    )
    for tabla in ("articulo_calzado", "articulo_confeccion", "articulo_maquila"):
        cursor.execute(
            f"DELETE FROM {tabla} WHERE id_articulo IN "
            f"(SELECT id_articulo FROM articulo WHERE id_venta = %s)",
            (id_venta,),
        )
    cursor.execute("DELETE FROM articulo       WHERE id_venta = %s", (id_venta,))
    cursor.execute("DELETE FROM pago_venta     WHERE id_venta = %s", (id_venta,))
    cursor.execute("DELETE FROM venta_historial WHERE id_venta = %s", (id_venta,))
    cursor.execute("DELETE FROM venta          WHERE id_venta = %s", (id_venta,))
    db_conn.commit()
    cursor.close()


@pytest.fixture
def logged_client(client, usuario_admin):
    """Flask test client con sesión de admin inyectada."""
    with client.session_transaction() as sess:
        sess["id_usuario"] = usuario_admin["id_usuario"]
        sess["usuario"] = usuario_admin["usuario"]
        sess["nombre"] = "Admin Test"
        sess["rol"] = "admin"
        sess["ultima_actividad"] = datetime.now().isoformat()
    return client
