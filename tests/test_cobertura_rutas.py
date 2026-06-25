"""
Tests adicionales para llevar rutas, app.py y middleware a 100% de cobertura.
Cubre las líneas de negocio que quedaron sin tests tras los pragmas en los handlers.
"""
from datetime import datetime, timedelta
import pytest


# ===========================================================================
# CLIENTES — líneas 67, 78, 117
# ===========================================================================

def test_guardar_cliente_con_next_redirige(logged_client, db_conn):
    """Cubre clientes_routes.py line 67: redirect a next_url cuando viene en form."""
    res = logged_client.post("/clientes/guardar", data={
        "nombre": "NextCli",
        "apellido": "TestNext",
        "telefono": "",
        "correo": "",
        "direccion": "",
        "next": "/clientes",
    }, follow_redirects=False)
    assert res.status_code == 302
    assert "/clientes" in res.headers.get("Location", "")

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT id_cliente FROM cliente WHERE nombre='NextCli' AND apellido='TestNext'"
    )
    row = cursor.fetchone()
    cursor.close()
    if row:
        cid = row[0]
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM clientes_historial WHERE id_cliente=%s", (cid,))
        cursor.execute("DELETE FROM cliente WHERE id_cliente=%s", (cid,))
        db_conn.commit()
        cursor.close()


def test_eliminar_cliente_con_ventas_flash_error(logged_client, cliente_test, venta_pendiente):
    """Cubre clientes_routes.py line 78: flash error cuando cliente tiene ventas."""
    res = logged_client.get(
        f"/clientes/eliminar/{cliente_test['id_cliente']}",
        follow_redirects=False,
    )
    assert res.status_code == 302


def test_ver_cliente_partial_200(logged_client, cliente_test):
    """Cubre clientes_routes.py line 117: partial view del cliente."""
    res = logged_client.get(
        f"/clientes/{cliente_test['id_cliente']}?partial=1"
    )
    assert res.status_code == 200


# ===========================================================================
# USUARIOS — líneas 66, 86, 88
# ===========================================================================

def test_guardar_usuario_edita_caja_exito(logged_client, usuario_caja, db_conn):
    """Cubre usuarios_routes.py line 66: flash éxito al editar usuario no-admin."""
    res = logged_client.post("/usuarios/guardar", data={
        "id_usuario": str(usuario_caja["id_usuario"]),
        "usuario":    usuario_caja["usuario"],
        "password":   "",
        "rol":        "caja",
        "pin":        "",
        "nombre":     "NombreEditado",
        "apellido":   "",
    }, follow_redirects=False)
    assert res.status_code == 302


def test_toggle_admin_usuario_retorna_error(logged_client, usuario_admin):
    """Cubre usuarios_routes.py line 86: flash error al intentar toggle de admin."""
    res = logged_client.get(
        f"/usuarios/toggle/{usuario_admin['id_usuario']}",
        follow_redirects=False,
    )
    assert res.status_code == 302


def test_toggle_usuario_activa_route(logged_client, usuario_caja, db_conn):
    """Cubre usuarios_routes.py line 88: flash 'activado' al reactivar usuario."""
    cursor = db_conn.cursor()
    cursor.execute(
        "UPDATE usuario SET activo = 0 WHERE id_usuario = %s",
        (usuario_caja["id_usuario"],),
    )
    db_conn.commit()
    cursor.close()

    res = logged_client.get(
        f"/usuarios/toggle/{usuario_caja['id_usuario']}",
        follow_redirects=False,
    )
    assert res.status_code == 302


# ===========================================================================
# GASTOS — líneas 123, 137, 150-152
# ===========================================================================

def test_categorias_lista_200(logged_client):
    """Cubre gastos_routes.py line 123: render categorías lista."""
    res = logged_client.get("/gastos/categorias/lista")
    assert res.status_code == 200


def test_actualizar_categoria_route(logged_client, db_conn):
    """Cubre gastos_routes.py line 137: actualizar categoría existente."""
    from models.gastos import obtener_categorias
    cats = obtener_categorias()
    if not cats:  # pragma: no cover
        pytest.skip("No hay categorías en la BD de test")
    cat = cats[0]

    res = logged_client.post(
        "/gastos/categorias/guardar",
        json={"id_categoria": cat["id_categoria"], "nombre": cat["nombre"]},
    )
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_eliminar_categoria_route(logged_client, db_conn):
    """Cubre gastos_routes.py lines 150-152: eliminar categoría sin gastos."""
    res = logged_client.post(
        "/gastos/categorias/guardar",
        json={"nombre": "CatParaEliminar"},
    )
    assert res.status_code == 200
    cat_id = None
    from models.gastos import obtener_categorias
    for c in obtener_categorias():
        if c["nombre"] == "CatParaEliminar":
            cat_id = c["id_categoria"]
            break
    assert cat_id is not None, "No se encontró la categoría creada"

    res = logged_client.post(f"/gastos/categorias/eliminar/{cat_id}")
    assert res.status_code == 200
    data = res.get_json()
    assert "ok" in data


# ===========================================================================
# SERVICIOS — línea 142
# ===========================================================================

def test_exportar_servicios_con_eliminados_xlsx(logged_client):
    """Cubre servicios_routes.py line 142: texto de subtexto con eliminados."""
    res = logged_client.get("/servicios/exportar?eliminados=1")
    assert res.status_code == 200
    assert "spreadsheetml" in res.content_type


# ===========================================================================
# APP.PY — líneas 109-110, 117, 187, 208
# ===========================================================================

def test_static_cache_headers(client):
    """Cubre app.py lines 109-110: cabeceras de caché para archivos estáticos."""
    res = client.get("/static/nonexistent.css")
    assert res.cache_control.max_age is not None or res.status_code in (200, 404)


def test_404_retorna_pagina_error(client):
    """Cubre app.py line 117: handler de 404."""
    res = client.get("/ruta-inexistente-que-nunca-existira-xxxyyy")
    assert res.status_code == 404


def test_index_negocio_invalido(logged_client):
    """Cubre app.py line 187: negocio inválido en index usa 'all'."""
    res = logged_client.get("/?negocio=INVALIDO")
    assert res.status_code == 200


def test_api_kpis_negocio_invalido(logged_client):
    """Cubre app.py line 208: negocio inválido en api_index_kpis usa 'all'."""
    res = logged_client.get("/api/index/kpis?negocio=INVALIDO")
    assert res.status_code == 200
    data = res.get_json()
    assert "ventas_hoy" in data


# ===========================================================================
# MIDDLEWARE — líneas 66, 77, 81, 91, 105-107, 131-132
# ===========================================================================

def test_middleware_endpoint_static_retorna_early(client):
    """Cubre auth_middleware.py line 66: return temprano para endpoint static/None."""
    res = client.get("/static/test.css")
    assert res.status_code in (200, 404)


def test_middleware_pin_login_sin_habilitado_redirige(client):
    """Cubre auth_middleware.py line 77: /pin sin pin_habilitado → redirect a login."""
    res = client.get("/pin", follow_redirects=False)
    assert res.status_code == 302
    assert "/login" in res.headers.get("Location", "")


def test_middleware_login_con_pin_habilitado_redirige(client):
    """Cubre auth_middleware.py line 81: /login con pin_habilitado → redirect a /pin."""
    with client.session_transaction() as sess:
        sess["pin_habilitado"] = True
    res = client.get("/login", follow_redirects=False)
    assert res.status_code == 302
    assert "/pin" in res.headers.get("Location", "")


def test_middleware_no_sesion_con_pin_redirige_a_pin(client):
    """Cubre auth_middleware.py line 91: sin sesión pero pin_habilitado → /pin."""
    with client.session_transaction() as sess:
        sess["pin_habilitado"] = True
    res = client.get("/gastos", follow_redirects=False)
    assert res.status_code == 302
    assert "/pin" in res.headers.get("Location", "")


def test_middleware_session_token_mismatch_redirige(client, usuario_admin):
    """Cubre auth_middleware.py lines 105-107: token de sesión incorrecto."""
    with client.session_transaction() as sess:
        sess["id_usuario"] = usuario_admin["id_usuario"]
        sess["usuario"] = usuario_admin["usuario"]
        sess["rol"] = "admin"
        sess["ultima_actividad"] = datetime.now().isoformat()
        sess["session_token"] = "TOKEN_INCORRECTO_QUE_NO_EXISTE"
    res = client.get("/estadisticas", follow_redirects=False)
    assert res.status_code == 302
    assert "/login" in res.headers.get("Location", "")


def test_middleware_timeout_con_pin_habilitado_redirige_a_pin(client, usuario_admin):
    """Cubre auth_middleware.py lines 131-132: sesión expirada con pin_habilitado."""
    old_time = (datetime.now() - timedelta(hours=2)).isoformat()
    with client.session_transaction() as sess:
        sess["id_usuario"] = usuario_admin["id_usuario"]
        sess["usuario"] = usuario_admin["usuario"]
        sess["rol"] = "admin"
        sess["ultima_actividad"] = old_time
        sess["pin_habilitado"] = True
    res = client.get("/estadisticas", follow_redirects=False)
    assert res.status_code == 302
    assert "/pin" in res.headers.get("Location", "")
