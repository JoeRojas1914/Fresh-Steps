"""
Tests para services/usuarios_service.py — CRUD de usuarios y toggle activo.
"""
import pytest
from werkzeug.security import generate_password_hash
from services.usuarios_service import (
    guardar_usuario_service,
    toggle_usuario_service,
    listar_usuarios_service,
)


def _crear_usuario_caja(db_conn, username="test_caja2_pytest", pin="1234"):
    """Helper: inserta un usuario caja directamente en BD."""
    cursor = db_conn.cursor()
    cursor.execute(
        """INSERT INTO usuario (usuario, password_hash, pin_hash, rol, nombre, activo)
           VALUES (%s, %s, %s, 'caja', 'Test Caja2', 1)""",
        (username, generate_password_hash("TestPass123!"), generate_password_hash(pin)),
    )
    db_conn.commit()
    uid = cursor.lastrowid
    cursor.close()
    return uid


def _cleanup_usuario(db_conn, uid, username):
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM historial_usuario WHERE id_usuario = %s", (uid,))
    cursor.execute("DELETE FROM login_log         WHERE id_usuario = %s", (uid,))
    cursor.execute("DELETE FROM login_intentos    WHERE usuario    = %s", (username,))
    cursor.execute("DELETE FROM usuario           WHERE id_usuario = %s", (uid,))
    db_conn.commit()
    cursor.close()


def test_crear_usuario_caja(app, db_conn):
    username = "test_nuevo_caja_pytest"
    with app.test_request_context("/"):
        from flask import session
        session["usuario"] = "admin_test"
        guardar_usuario_service(
            id_usuario=None,
            username=username,
            password="TestPass123!",
            rol="caja",
            pin="4321",
            nombre="Nuevo",
        )

    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT id_usuario, activo FROM usuario WHERE usuario = %s", (username,))
    row = cursor.fetchone()
    cursor.close()

    assert row is not None
    assert row["activo"] == 1

    _cleanup_usuario(db_conn, row["id_usuario"], username)


def test_crear_usuario_sin_password_lanza_error(app):
    with app.test_request_context("/"):
        from flask import session
        session["usuario"] = "admin_test"
        with pytest.raises(ValueError, match="Password"):
            guardar_usuario_service(
                id_usuario=None,
                username="usuario_sin_pass",
                password="",
                rol="caja",
                pin="1234",
            )


def test_editar_usuario_actualiza_nombre(app, db_conn):
    username = "test_editar_pytest"
    uid = _crear_usuario_caja(db_conn, username)

    with app.test_request_context("/"):
        from flask import session
        session["usuario"] = "admin_test"
        guardar_usuario_service(
            id_usuario=uid,
            username=username,
            password="",
            rol="caja",
            pin="",
            nombre="NombreActualizado",
        )

    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT nombre FROM usuario WHERE id_usuario = %s", (uid,))
    row = cursor.fetchone()
    cursor.close()
    assert row["nombre"] == "NombreActualizado"

    _cleanup_usuario(db_conn, uid, username)


def test_toggle_usuario_desactiva_y_reactiva(app, db_conn):
    username = "test_toggle_pytest"
    uid = _crear_usuario_caja(db_conn, username)

    with app.test_request_context("/"):
        from flask import session
        session["usuario"] = "admin_test"
        nuevo_estado = toggle_usuario_service(uid)
    assert nuevo_estado == 0

    with app.test_request_context("/"):
        from flask import session
        session["usuario"] = "admin_test"
        nuevo_estado = toggle_usuario_service(uid)
    assert nuevo_estado == 1

    _cleanup_usuario(db_conn, uid, username)


def test_toggle_admin_no_cambia(app, db_conn):
    """El rol admin no puede ser desactivado."""
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT id_usuario FROM usuario WHERE rol = 'admin' LIMIT 1")
    admin = cursor.fetchone()
    cursor.close()

    if not admin:
        pytest.skip("No hay usuario admin en la BD de test")

    with app.test_request_context("/"):
        from flask import session
        session["usuario"] = "admin_test"
        resultado = toggle_usuario_service(admin["id_usuario"])
    assert resultado is None


def test_listar_usuarios_filtra_por_rol(db_conn):
    usuarios = listar_usuarios_service(rol="admin")
    assert all(u["rol"] == "admin" for u in usuarios)


def test_listar_usuarios_filtra_activos(db_conn):
    usuarios = listar_usuarios_service(activo=1)
    assert all(u["activo"] == 1 for u in usuarios)
