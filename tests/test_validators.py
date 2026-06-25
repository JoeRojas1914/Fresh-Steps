"""
Tests para validators.py — funciones de validación puras, sin DB.
"""
import pytest
from validators import (
    validar_correo,
    validar_telefono,
    validar_nombre,
    validar_pin,
    validar_password,
)


# ---------------------------------------------------------------------------
# validar_correo
# ---------------------------------------------------------------------------

def test_correo_valido():
    assert validar_correo("user@example.com") == "user@example.com"


def test_correo_con_espacios_se_limpia():
    assert validar_correo("  user@example.com  ") == "user@example.com"


def test_correo_vacio_devuelve_none():
    assert validar_correo("") is None
    assert validar_correo(None) is None
    assert validar_correo("   ") is None


def test_correo_invalido_lanza_error():
    with pytest.raises(ValueError):
        validar_correo("no-es-correo")

    with pytest.raises(ValueError):
        validar_correo("@dominio.com")

    with pytest.raises(ValueError):
        validar_correo("user@")


# ---------------------------------------------------------------------------
# validar_telefono
# ---------------------------------------------------------------------------

def test_telefono_valido():
    assert validar_telefono("5512345678") == "5512345678"


def test_telefono_con_guiones_y_espacios():
    assert validar_telefono("55-1234-5678") == "5512345678"


def test_telefono_vacio_devuelve_none():
    assert validar_telefono("") is None
    assert validar_telefono(None) is None


def test_telefono_corto_lanza_error():
    with pytest.raises(ValueError):
        validar_telefono("12345")


def test_telefono_largo_lanza_error():
    with pytest.raises(ValueError):
        validar_telefono("55123456789")


def test_telefono_con_letras_lanza_error():
    with pytest.raises(ValueError):
        validar_telefono("5512abc678")


# ---------------------------------------------------------------------------
# validar_nombre
# ---------------------------------------------------------------------------

def test_nombre_valido():
    assert validar_nombre("Juan") == "Juan"


def test_nombre_limpia_espacios():
    assert validar_nombre("  María  ") == "María"


def test_nombre_vacio_lanza_error():
    with pytest.raises(ValueError, match="obligatorio"):
        validar_nombre("")

    with pytest.raises(ValueError):
        validar_nombre(None)


def test_nombre_demasiado_largo_lanza_error():
    with pytest.raises(ValueError, match="100"):
        validar_nombre("x" * 101)


def test_nombre_campo_personalizado():
    with pytest.raises(ValueError, match="Apellido"):
        validar_nombre("", campo="Apellido")


# ---------------------------------------------------------------------------
# validar_pin
# ---------------------------------------------------------------------------

def test_pin_4_digitos():
    assert validar_pin("1234") == "1234"


def test_pin_6_digitos():
    assert validar_pin("123456") == "123456"


def test_pin_vacio_devuelve_none():
    assert validar_pin("") is None
    assert validar_pin(None) is None


def test_pin_3_digitos_lanza_error():
    with pytest.raises(ValueError):
        validar_pin("123")


def test_pin_7_digitos_lanza_error():
    with pytest.raises(ValueError):
        validar_pin("1234567")


def test_pin_con_letras_lanza_error():
    with pytest.raises(ValueError):
        validar_pin("12ab")


# ---------------------------------------------------------------------------
# validar_password
# ---------------------------------------------------------------------------

def test_password_valida():
    assert validar_password("Segura1x") == "Segura1x"


def test_password_vacia_no_obligatoria_devuelve_none():
    assert validar_password("") is None
    assert validar_password(None) is None


def test_password_vacia_obligatoria_lanza_error():
    with pytest.raises(ValueError, match="obligatoria"):
        validar_password("", obligatorio=True)

    with pytest.raises(ValueError):
        validar_password(None, obligatorio=True)


def test_password_corta_lanza_error():
    with pytest.raises(ValueError, match="8"):
        validar_password("Ab1")


def test_password_sin_mayuscula_lanza_error():
    with pytest.raises(ValueError, match="mayúscula"):
        validar_password("password1")


def test_password_sin_numero_lanza_error():
    with pytest.raises(ValueError, match="número"):
        validar_password("Passwords")


def test_password_limite_inferior_valida():
    assert validar_password("Abcdef1x") is not None
