"""
Tests de seguridad: CSRF, timeout de sesión y rate limiting.
"""

import pytest
from datetime import datetime, timedelta


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def csrf_client(app):
    """Cliente con CSRF activado. Restaura la config al terminar."""
    app.config["WTF_CSRF_ENABLED"] = True
    yield app.test_client()
    app.config["WTF_CSRF_ENABLED"] = False


def _sesion_admin(client, usuario_admin, ultima_actividad=None):
    with client.session_transaction() as sess:
        sess["id_usuario"]      = usuario_admin["id_usuario"]
        sess["usuario"]         = usuario_admin["usuario"]
        sess["rol"]             = "admin"
        sess["ultima_actividad"] = (ultima_actividad or datetime.now()).isoformat()


def _sesion_caja(client, usuario_caja, ultima_actividad=None):
    with client.session_transaction() as sess:
        sess["id_usuario"]      = usuario_caja["id_usuario"]
        sess["usuario"]         = usuario_caja["usuario"]
        sess["rol"]             = "caja"
        sess["ultima_actividad"] = (ultima_actividad or datetime.now()).isoformat()


# ─── CSRF ─────────────────────────────────────────────────────────────────────

def test_csrf_rechaza_post_sin_token(csrf_client, usuario_admin):
    """POST sin token CSRF debe retornar 400."""
    _sesion_admin(csrf_client, usuario_admin)
    res = csrf_client.post("/clientes/guardar", data={
        "nombre": "TestCSRF", "apellido": "Apellido",
        "telefono": "5512345678", "correo": "", "direccion": "",
    })
    assert res.status_code == 400


def test_csrf_rechaza_post_token_invalido(csrf_client, usuario_admin):
    """POST con token CSRF inválido debe retornar 400."""
    _sesion_admin(csrf_client, usuario_admin)
    res = csrf_client.post("/clientes/guardar", data={
        "nombre": "TestCSRF", "apellido": "Apellido",
        "telefono": "5512345678",
        "csrf_token": "token-invalido-xxx",
    })
    assert res.status_code == 400


# ─── Timeout de sesión ────────────────────────────────────────────────────────

def test_sesion_admin_expirada_redirige(client, usuario_admin):
    """Admin inactivo >15 min debe ser redirigido al login."""
    vencida = datetime.now() - timedelta(minutes=20)
    _sesion_admin(client, usuario_admin, ultima_actividad=vencida)

    res = client.get("/clientes")
    assert res.status_code in (302, 401)
    location = res.headers.get("Location", "")
    assert "/login" in location or res.status_code == 401


def test_sesion_caja_expirada_redirige(client, usuario_caja):
    """Caja inactiva >20 min debe ser redirigida."""
    vencida = datetime.now() - timedelta(minutes=25)
    _sesion_caja(client, usuario_caja, ultima_actividad=vencida)

    res = client.get("/ventas")
    assert res.status_code in (302, 401)


def test_sesion_admin_activa_no_expira(client, usuario_admin):
    """Admin con actividad reciente no debe ser rechazado."""
    reciente = datetime.now() - timedelta(minutes=5)
    _sesion_admin(client, usuario_admin, ultima_actividad=reciente)

    res = client.get("/clientes")
    assert res.status_code == 200


def test_sesion_caja_activa_no_expira(client, usuario_caja):
    """Caja con actividad reciente no debe ser rechazada."""
    reciente = datetime.now() - timedelta(minutes=10)
    _sesion_caja(client, usuario_caja, ultima_actividad=reciente)

    res = client.get("/ventas")
    assert res.status_code == 200


def test_sin_ultima_actividad_se_permite_y_se_establece(client, usuario_admin):
    """Sesión sin ultima_actividad es permitida; el middleware la inicializa en el primer request."""
    with client.session_transaction() as sess:
        sess["id_usuario"] = usuario_admin["id_usuario"]
        sess["usuario"]    = usuario_admin["usuario"]
        sess["rol"]        = "admin"
        # No se setea ultima_actividad

    res = client.get("/clientes")
    assert res.status_code == 200

    # Verificar que el middleware la estableció
    with client.session_transaction() as sess:
        assert "ultima_actividad" in sess


# ─── Rate limiting ────────────────────────────────────────────────────────────
# Se usa REMOTE_ADDR 10.0.0.1 para aislar estos tests del contador compartido.

_IP_RATE = "10.0.0.1"


def test_rate_limit_usuarios_bloquea_al_superar(app, usuario_admin):
    """Más de 20 POSTs a /usuarios/guardar desde la misma IP → 429."""
    client = app.test_client()
    _sesion_admin(client, usuario_admin)

    for _ in range(20):
        client.post("/usuarios/guardar",
                    environ_overrides={"REMOTE_ADDR": _IP_RATE},
                    data={"usuario": "x", "password": "Test1234!", "pin": "1234", "rol": "caja"})

    res = client.post("/usuarios/guardar",
                      environ_overrides={"REMOTE_ADDR": _IP_RATE},
                      data={"usuario": "x", "password": "Test1234!", "pin": "1234", "rol": "caja"})
    assert res.status_code == 429


def test_rate_limit_clientes_bloquea_al_superar(app, usuario_admin, db_conn):
    """Más de 30 POSTs a /clientes/guardar desde la misma IP → 429."""
    client = app.test_client()
    _sesion_admin(client, usuario_admin)

    for i in range(30):
        client.post("/clientes/guardar",
                    environ_overrides={"REMOTE_ADDR": _IP_RATE},
                    data={"nombre": f"RL{i}", "apellido": "Test",
                          "telefono": "5512345678", "correo": "", "direccion": ""})

    res = client.post("/clientes/guardar",
                      environ_overrides={"REMOTE_ADDR": _IP_RATE},
                      data={"nombre": "RLFinal", "apellido": "Test",
                            "telefono": "5512345678", "correo": "", "direccion": ""})
    assert res.status_code == 429

    # Cleanup clientes creados por este test
    cursor = db_conn.cursor()
    cursor.execute("SELECT id_cliente FROM cliente WHERE apellido = 'Test' AND nombre LIKE 'RL%'")
    ids = [r[0] for r in cursor.fetchall()]
    if ids:
        fmt = ",".join(["%s"] * len(ids))
        cursor.execute(f"DELETE FROM clientes_historial WHERE id_cliente IN ({fmt})", ids)
        cursor.execute(f"DELETE FROM cliente WHERE id_cliente IN ({fmt})", ids)
    db_conn.commit()
    cursor.close()
