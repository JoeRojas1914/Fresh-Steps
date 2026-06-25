"""
Tests HTTP para routes/auth_routes.py.
Cubre: _poblar_sesion, login GET/POST (válido admin_mode, redirige a pin,
       credenciales incorrectas, cuenta bloqueada), pin_login GET/POST
       (pin correcto, incorrecto, bloqueado), logout (con/sin pin_habilitado,
       sin username en sesión).

REMOTE_ADDR 127.0.0.3 aísla todos los intentos del contador compartido en
127.0.0.1 que usa el resto del suite.
"""
from datetime import datetime

_IP = "127.0.0.3"


def _req(method, client, path, **kwargs):
    """Wrapper que inyecta REMOTE_ADDR fijo para no afectar el rate limiter global."""
    kwargs.setdefault("environ_overrides", {})["REMOTE_ADDR"] = _IP
    return getattr(client, method)(path, **kwargs)


def _set_session(client, **kwargs):
    with client.session_transaction() as sess:
        sess.update(kwargs)


# ===========================================================================
# LOGIN — GET
# ===========================================================================

def test_login_get_retorna_200(client):
    res = _req("get", client, "/login")
    assert res.status_code == 200


# ===========================================================================
# LOGIN — POST: credenciales incorrectas  →  re-render 200
# ===========================================================================

def test_login_post_invalido_rerender_200(client):
    res = _req("post", client, "/login", data={
        "usuario":  "noexiste_xyz_pytest",
        "password": "wrongpassword",
    })
    assert res.status_code == 200


# ===========================================================================
# LOGIN — POST: cuenta bloqueada → cubre lines 39-41
# ===========================================================================

def test_login_post_cuenta_bloqueada(client, usuario_admin, db_conn):
    """Pre-pobla login_intentos hasta bloqueado → POST devuelve LOCKED (200)."""
    from models.login import registrar_fallo
    from config import MAX_INTENTOS_LOGIN

    un = usuario_admin["usuario"]
    for _ in range(MAX_INTENTOS_LOGIN):
        registrar_fallo(un, _IP)

    res = _req("post", client, "/login", data={
        "usuario":  un,
        "password": "cualquier_cosa",
    })
    assert res.status_code in (200, 302)

    # Limpieza de intentos (fixture también borra al teardown)
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM login_intentos WHERE usuario = %s", (un,))
    db_conn.commit()
    cursor.close()


# ===========================================================================
# LOGIN — POST válido + admin=1 → redirect a index, cubre _poblar_sesion
# ===========================================================================

def test_login_post_admin_mode_redirige_a_index(client, usuario_admin):
    res = _req("post", client, "/login?admin=1", data={
        "usuario":  usuario_admin["usuario"],
        "password": usuario_admin["password"],
    }, follow_redirects=False)
    assert res.status_code == 302
    assert "pin" not in res.headers.get("Location", "")


# ===========================================================================
# LOGIN — POST válido sin admin=1 → redirect a /pin
# ===========================================================================

def test_login_post_sin_admin_mode_redirige_a_pin(client, usuario_admin):
    res = _req("post", client, "/login", data={
        "usuario":  usuario_admin["usuario"],
        "password": usuario_admin["password"],
    }, follow_redirects=False)
    assert res.status_code == 302
    assert "pin" in res.headers.get("Location", "")


# ===========================================================================
# PIN LOGIN — GET con pin_habilitado → 200
# ===========================================================================

def test_pin_get_con_habilitado_retorna_200(client):
    _set_session(client, pin_habilitado=True)
    res = _req("get", client, "/pin")
    assert res.status_code == 200


# ===========================================================================
# PIN LOGIN — POST con PIN incorrecto → re-render 200
# ===========================================================================

def test_pin_post_incorrecto_rerender_200(client, usuario_caja, db_conn):
    """PIN incorrecto → flash 'PIN incorrecto' y re-render (lines 87-89)."""
    # Limpiar intentos acumulados de usuarios seed para garantizar that
    # login_pin_service retorna None (no LOCKED), cubriendo lines 87-89.
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM login_intentos WHERE ip = %s", (_IP,))
    db_conn.commit()
    cursor.close()

    _set_session(client, pin_habilitado=True)
    res = _req("post", client, "/pin", data={"pin": "0000"})
    assert res.status_code == 200

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM login_intentos WHERE ip = %s", (_IP,))
    db_conn.commit()
    cursor.close()


# ===========================================================================
# PIN LOGIN — POST con PIN bloqueado → cubre lines 83-85
# ===========================================================================

def test_pin_post_bloqueado(client, usuario_caja, db_conn):
    """Pre-pobla intentos hasta bloqueado → POST devuelve LOCKED (200)."""
    from models.login import registrar_fallo
    from config import MAX_INTENTOS_PIN, BLOQUEO_MIN_PIN

    un = usuario_caja["usuario"]
    for _ in range(MAX_INTENTOS_PIN):
        registrar_fallo(un, _IP, max_intentos=MAX_INTENTOS_PIN, bloqueo_min=BLOQUEO_MIN_PIN)

    _set_session(client, pin_habilitado=True)
    res = _req("post", client, "/pin", data={"pin": "0000"})
    assert res.status_code in (200, 302)

    # Limpiar todos los intentos para esta IP (incluye seed users)
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM login_intentos WHERE ip = %s", (_IP,))
    db_conn.commit()
    cursor.close()


# ===========================================================================
# PIN LOGIN — POST con PIN correcto → redirect a index
# ===========================================================================

def test_pin_post_correcto_redirige(client, usuario_caja):
    _set_session(client, pin_habilitado=True)
    res = _req("post", client, "/pin",
               data={"pin": usuario_caja["pin"]},
               follow_redirects=False)
    assert res.status_code == 302


# ===========================================================================
# LOGOUT — sesión completa con pin_habilitado → redirige a /pin
# ===========================================================================

def test_logout_con_pin_habilitado_redirige_a_pin(client, usuario_admin):
    _set_session(
        client,
        id_usuario=usuario_admin["id_usuario"],
        usuario=usuario_admin["usuario"],
        pin_habilitado=True,
        ultima_actividad=datetime.now().isoformat(),
        rol="admin",
    )
    res = _req("get", client, "/logout", follow_redirects=False)
    assert res.status_code == 302
    assert "pin" in res.headers.get("Location", "")


# ===========================================================================
# LOGOUT — sesión sin pin_habilitado → redirige a /login
# ===========================================================================

def test_logout_sin_pin_habilitado_redirige_a_login(client, usuario_admin):
    _set_session(
        client,
        id_usuario=usuario_admin["id_usuario"],
        usuario=usuario_admin["usuario"],
        ultima_actividad=datetime.now().isoformat(),
        rol="admin",
    )
    res = _req("get", client, "/logout", follow_redirects=False)
    assert res.status_code == 302
    assert "login" in res.headers.get("Location", "")


# ===========================================================================
# LOGOUT — sesión sin username → cubre `if username:` → False
# ===========================================================================

def test_logout_sin_username_en_sesion(client, usuario_admin):
    """id_usuario presente pero sin 'usuario' → invalidar_session_token corre
    pero registrar_logout no. Cubre la rama False de 'if username:'."""
    _set_session(
        client,
        id_usuario=usuario_admin["id_usuario"],
        ultima_actividad=datetime.now().isoformat(),
        rol="admin",
    )
    res = _req("get", client, "/logout", follow_redirects=False)
    assert res.status_code == 302
