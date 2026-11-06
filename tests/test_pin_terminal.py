"""Acceso por PIN: bloqueo por terminal y PIN únicos (hallazgo C6 de reviews/audit-plan-full.md).

Antes cada PIN incorrecto sumaba un fallo a CADA cajero, así que unos pocos
errores de dedo bloqueaban a toda la tienda. Ahora:
- los fallos se cuentan una vez por intento y por terminal (IP)
- tras MAX_INTENTOS_PIN fallos la terminal espera BLOQUEO_MIN_PIN minutos
- un admin que entra con contraseña en esa terminal la desbloquea
- un PIN repetido en dos usuarios nunca deja entrar con uno al azar
"""
from datetime import datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

from config import MAX_INTENTOS_PIN, CLAVE_PIN_TERMINAL
from services.auth_service import login_password_service, login_pin_service

IP = "10.77.0.1"


@pytest.fixture(autouse=True)
def _terminal_limpia():
    from tests.conftest import limpiar_bloqueo_pin_terminal
    limpiar_bloqueo_pin_terminal()
    yield
    limpiar_bloqueo_pin_terminal()
OTRA_IP = "10.77.0.2"


def _pin(app, pin, ip=IP):
    with app.test_request_context("/", headers={"User-Agent": "pytest"}):
        return login_pin_service(pin, ip)


def _intentos(db_conn, usuario, ip=IP):
    db_conn.commit()
    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT intentos, bloqueado_hasta FROM login_intentos WHERE usuario = %s AND ip = %s",
                (usuario, ip))
    row = cur.fetchone()
    cur.close()
    return row


@pytest.fixture
def caja_extra(db_conn):
    """Segundo usuario de caja, para comprobar que los fallos no se multiplican por cajero."""
    cur = db_conn.cursor()
    cur.execute("""INSERT INTO usuario (usuario, password_hash, pin_hash, rol, nombre, activo)
                   VALUES ('test_caja2_pytest', %s, %s, 'caja', 'Caja Dos', 1)""",
                (generate_password_hash("TestPass123!"), generate_password_hash("5555")))
    uid = cur.lastrowid
    db_conn.commit()
    cur.close()
    yield {"id_usuario": uid, "usuario": "test_caja2_pytest", "pin": "5555"}
    cur = db_conn.cursor()
    cur.execute("DELETE FROM login_log WHERE id_usuario = %s", (uid,))
    cur.execute("DELETE FROM login_intentos WHERE usuario = 'test_caja2_pytest'")
    cur.execute("DELETE FROM historial_usuario WHERE id_usuario = %s", (uid,))
    cur.execute("DELETE FROM usuario WHERE id_usuario = %s", (uid,))
    db_conn.commit()
    cur.close()


# ── Conteo por terminal ───────────────────────────────────────────────────────

def test_un_pin_incorrecto_suma_un_solo_fallo_a_la_terminal(app, db_conn, usuario_caja, caja_extra):
    assert _pin(app, "0000") is None
    assert _intentos(db_conn, CLAVE_PIN_TERMINAL)["intentos"] == 1
    # Ya no se registra un fallo por cada cajero
    assert _intentos(db_conn, usuario_caja["usuario"]) is None
    assert _intentos(db_conn, caja_extra["usuario"]) is None


def test_errores_por_debajo_del_limite_no_bloquean(app, usuario_caja, caja_extra):
    for _ in range(MAX_INTENTOS_PIN - 1):
        assert _pin(app, "0000") is None
    resultado = _pin(app, usuario_caja["pin"])
    assert isinstance(resultado, dict) and resultado["usuario"] == usuario_caja["usuario"]


def test_acceso_correcto_reinicia_el_contador(app, db_conn, usuario_caja):
    _pin(app, "0000")
    _pin(app, usuario_caja["pin"])
    assert _intentos(db_conn, CLAVE_PIN_TERMINAL) is None


def test_al_llegar_al_limite_la_terminal_se_bloquea(app, usuario_caja):
    resultados = [_pin(app, "0000") for _ in range(MAX_INTENTOS_PIN)]
    assert resultados[-1] == "LOCKED"
    # Bloqueada: ni el PIN correcto entra
    assert _pin(app, usuario_caja["pin"]) == "LOCKED"


def test_el_bloqueo_no_afecta_a_otra_terminal(app, usuario_caja):
    for _ in range(MAX_INTENTOS_PIN):
        _pin(app, "0000")
    resultado = _pin(app, usuario_caja["pin"], ip=OTRA_IP)
    assert isinstance(resultado, dict)


def test_tras_vencer_el_bloqueo_se_vuelve_a_contar_desde_cero(app, db_conn, usuario_caja):
    for _ in range(MAX_INTENTOS_PIN):
        _pin(app, "0000")
    cur = db_conn.cursor()
    cur.execute("UPDATE login_intentos SET bloqueado_hasta = %s WHERE usuario = %s AND ip = %s",
                (datetime.now() - timedelta(minutes=1), CLAVE_PIN_TERMINAL, IP))
    db_conn.commit()
    cur.close()
    # Un error después del bloqueo vencido ya no vuelve a bloquear de inmediato
    assert _pin(app, "0000") is None
    assert _intentos(db_conn, CLAVE_PIN_TERMINAL)["intentos"] == 1


def test_admin_con_contrasena_desbloquea_la_terminal(app, db_conn, usuario_admin, usuario_caja):
    for _ in range(MAX_INTENTOS_PIN):
        _pin(app, "0000")
    assert _pin(app, usuario_caja["pin"]) == "LOCKED"

    with app.test_request_context("/", headers={"User-Agent": "pytest"}):
        admin = login_password_service(usuario_admin["usuario"], usuario_admin["password"], IP)
    assert isinstance(admin, dict)
    assert _intentos(db_conn, CLAVE_PIN_TERMINAL) is None
    assert isinstance(_pin(app, usuario_caja["pin"]), dict)


def test_pin_vacio_no_cuenta_como_fallo(app, db_conn, usuario_caja):
    assert _pin(app, "") is None
    assert _pin(app, None) is None
    assert _intentos(db_conn, CLAVE_PIN_TERMINAL) is None


# ── PIN duplicados ────────────────────────────────────────────────────────────

def test_pin_duplicado_no_entra_con_ningun_usuario(app, db_conn, usuario_caja, caja_extra):
    cur = db_conn.cursor()
    cur.execute("UPDATE usuario SET pin_hash = %s WHERE id_usuario = %s",
                (generate_password_hash(usuario_caja["pin"]), caja_extra["id_usuario"]))
    db_conn.commit()
    cur.close()
    assert _pin(app, usuario_caja["pin"]) == "DUPLICADO"


def test_ruta_pin_duplicado_muestra_mensaje(client, db_conn, usuario_caja, caja_extra):
    cur = db_conn.cursor()
    cur.execute("UPDATE usuario SET pin_hash = %s WHERE id_usuario = %s",
                (generate_password_hash(usuario_caja["pin"]), caja_extra["id_usuario"]))
    db_conn.commit()
    cur.close()
    with client.session_transaction() as s:
        s["pin_habilitado"] = True
    res = client.post("/pin", data={"pin": usuario_caja["pin"]},
                      environ_overrides={"REMOTE_ADDR": IP})
    assert res.status_code == 200
    assert "repetido en más de un usuario" in res.data.decode()
    with client.session_transaction() as s:
        assert "id_usuario" not in s


def test_no_se_puede_reusar_el_pin_de_un_usuario_inactivo(app, db_conn, caja_extra):
    """Antes solo se comparaba contra usuarios activos: al reactivar, dos usuarios
    quedaban con el mismo PIN."""
    from services.usuarios_service import guardar_usuario_service
    cur = db_conn.cursor()
    cur.execute("UPDATE usuario SET activo = 0 WHERE id_usuario = %s", (caja_extra["id_usuario"],))
    db_conn.commit()
    cur.close()
    with app.test_request_context("/"):
        with pytest.raises(ValueError, match="PIN ya está en uso"):
            guardar_usuario_service(None, "test_caja3_pytest", "TestPass123!", "caja",
                                    caja_extra["pin"], negocios=[1])


def test_pin_con_espacios_se_guarda_limpio(app, db_conn):
    """validar_pin quita espacios; antes se hasheaba el valor original con espacios."""
    from services.usuarios_service import guardar_usuario_service
    with app.test_request_context("/"):
        guardar_usuario_service(None, "test_caja4_pytest", "TestPass123!", "caja", " 8642 ", negocios=[1])
    try:
        assert isinstance(_pin(app, "8642"), dict)
    finally:
        cur = db_conn.cursor(dictionary=True)
        cur.execute("SELECT id_usuario FROM usuario WHERE usuario = 'test_caja4_pytest'")
        uid = cur.fetchone()["id_usuario"]
        for sql in ("DELETE FROM usuario_negocio WHERE id_usuario = %s",
                    "DELETE FROM historial_usuario WHERE id_usuario = %s",
                    "DELETE FROM login_log WHERE id_usuario = %s",
                    "DELETE FROM usuario WHERE id_usuario = %s"):
            cur.execute(sql, (uid,))
        cur.execute("DELETE FROM login_intentos WHERE usuario = 'test_caja4_pytest'")
        db_conn.commit()
        cur.close()
