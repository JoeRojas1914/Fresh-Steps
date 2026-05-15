"""
Tests para services/auth_service.py — login por contraseña y por PIN.
Se usa app.test_request_context() porque el servicio llama a request.headers.
"""
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
