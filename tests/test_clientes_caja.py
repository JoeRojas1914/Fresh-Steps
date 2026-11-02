"""
Clientes para usuarios de caja.

La caja ve solo los clientes con compras en sus negocios y, en el perfil,
solo los pedidos de esos negocios. No puede eliminar/restaurar clientes,
ver eliminados ni exportar a Excel.

venta_pendiente (Calzado, 1) y venta_confeccion (Confección, 2) son del mismo cliente_test.
"""


def _asignar_negocios(db_conn, id_usuario, ids):
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM usuario_negocio WHERE id_usuario = %s", (id_usuario,))
    for id_negocio in ids:
        cursor.execute(
            "INSERT INTO usuario_negocio (id_usuario, id_negocio) VALUES (%s, %s)",
            (id_usuario, id_negocio),
        )
    db_conn.commit()
    cursor.close()


def _link_perfil(id_cliente):
    return f'data-href="/clientes/{id_cliente}"'.encode()


def _fila_venta(id_venta):
    return f'id="detalles-{id_venta}"'.encode()


# ---------------------------------------------------------------------------
# Acceso y controles ocultos
# ---------------------------------------------------------------------------

def test_caja_puede_abrir_clientes(logged_client_caja):
    res = logged_client_caja.get("/clientes")
    assert res.status_code == 200
    assert b'id="form-filtro-clientes"' in res.data


def test_caja_ve_enlace_clientes_en_menu(logged_client_caja):
    assert b'href="/clientes"' in logged_client_caja.get("/ventas/pendientes").data


def test_caja_no_ve_toggle_eliminados_ni_exportar(logged_client_caja):
    html = logged_client_caja.get("/clientes").data.decode()
    assert 'id="toggle-eliminados"' not in html
    assert "Exportar Excel" not in html


def test_caja_no_ve_boton_eliminar(logged_client_caja, cliente_test, venta_pendiente):
    html = logged_client_caja.get("/clientes?partial=1&q=TestNombre").data.decode()
    assert f'data-href="/clientes/{cliente_test["id_cliente"]}"' in html
    assert "js-confirmar-eliminar-cliente" not in html
    assert "js-restaurar-cliente" not in html


def test_admin_sigue_viendo_toggle_exportar_y_eliminar(logged_client, cliente_test):
    html = logged_client.get("/clientes?q=TestNombre").data.decode()
    assert 'id="toggle-eliminados"' in html
    assert "Exportar Excel" in html
    assert "js-confirmar-eliminar-cliente" in html


def test_caja_no_puede_exportar_clientes(logged_client_caja, cliente_test):
    assert logged_client_caja.get("/clientes/exportar").status_code == 403
    assert logged_client_caja.get(f"/clientes/{cliente_test['id_cliente']}/exportar").status_code == 403


def test_caja_no_puede_eliminar_ni_restaurar(logged_client_caja, cliente_test):
    cid = cliente_test["id_cliente"]
    assert logged_client_caja.post(f"/clientes/eliminar/{cid}").status_code == 403
    assert logged_client_caja.post(f"/clientes/restaurar/{cid}").status_code == 403


# ---------------------------------------------------------------------------
# Listado: solo clientes con compras en sus negocios
# ---------------------------------------------------------------------------

def test_caja_ve_cliente_con_compras_en_su_negocio(
    logged_client_caja, usuario_caja, db_conn, cliente_test, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [1])
    res = logged_client_caja.get("/clientes?partial=1&q=TestNombre")
    assert _link_perfil(cliente_test["id_cliente"]) in res.data


def test_caja_no_ve_cliente_sin_compras_en_sus_negocios(
    logged_client_caja, usuario_caja, db_conn, cliente_test, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    res = logged_client_caja.get("/clientes?partial=1&q=TestNombre")
    assert _link_perfil(cliente_test["id_cliente"]) not in res.data


def test_caja_no_ve_cliente_sin_compras(logged_client_caja, cliente_test):
    res = logged_client_caja.get("/clientes?partial=1&q=TestNombre")
    assert _link_perfil(cliente_test["id_cliente"]) not in res.data


def test_caja_no_ve_eliminados_aunque_lo_pida(
    logged_client_caja, db_conn, cliente_test, venta_pendiente
):
    cursor = db_conn.cursor()
    cursor.execute("UPDATE cliente SET activo = 0 WHERE id_cliente = %s", (cliente_test["id_cliente"],))
    db_conn.commit()
    cursor.close()
    res = logged_client_caja.get("/clientes?partial=1&eliminados=1&q=TestNombre")
    assert _link_perfil(cliente_test["id_cliente"]) not in res.data


def test_caja_pedidos_del_listado_cuentan_solo_sus_negocios(
    usuario_caja, db_conn, cliente_test, venta_pendiente, venta_confeccion
):
    from services.clientes_service import listar_clientes_service
    data = listar_clientes_service(q="TestNombre", por_pagina=200, id_negocio=[2])
    fila = next(c for c in data["clientes"] if c["id_cliente"] == cliente_test["id_cliente"])
    todos = listar_clientes_service(q="TestNombre", por_pagina=200)
    fila_todos = next(c for c in todos["clientes"] if c["id_cliente"] == cliente_test["id_cliente"])
    assert fila["total_pedidos"] == 1
    assert fila_todos["total_pedidos"] == 2


# ---------------------------------------------------------------------------
# Perfil e historial de pedidos
# ---------------------------------------------------------------------------

def test_caja_no_puede_abrir_perfil_de_cliente_ajeno(
    logged_client_caja, usuario_caja, db_conn, cliente_test, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    assert logged_client_caja.get(f"/clientes/{cliente_test['id_cliente']}").status_code == 403


def test_caja_perfil_solo_muestra_pedidos_de_sus_negocios(
    logged_client_caja, usuario_caja, db_conn, cliente_test, venta_pendiente, venta_confeccion
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    res = logged_client_caja.get(f"/clientes/{cliente_test['id_cliente']}")
    assert res.status_code == 200
    assert _fila_venta(venta_confeccion["id_venta"]) in res.data
    assert _fila_venta(venta_pendiente["id_venta"]) not in res.data
    assert b'kpi-card__value">1<' in res.data
    assert b"Exportar Excel" not in res.data


def test_caja_no_puede_forzar_otro_negocio_en_perfil(
    logged_client_caja, usuario_caja, db_conn, cliente_test, venta_pendiente, venta_confeccion
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    res = logged_client_caja.get(f"/clientes/{cliente_test['id_cliente']}?partial=1&id_negocio=1")
    assert _fila_venta(venta_pendiente["id_venta"]) not in res.data


def test_caja_kpis_solo_de_sus_negocios(
    cliente_test, venta_pendiente, venta_confeccion
):
    from models.ventas_detalles import obtener_kpis_cliente
    cid = cliente_test["id_cliente"]
    todos      = obtener_kpis_cliente(cid)["total_gastado"]
    calzado    = obtener_kpis_cliente(cid, [1])["total_gastado"]
    confeccion = obtener_kpis_cliente(cid, [2])["total_gastado"]
    assert calzado > 0 and confeccion > 0
    assert round(calzado + confeccion, 2) == round(todos, 2)


def test_caja_perfil_no_muestra_montos(logged_client_caja, cliente_test, venta_pendiente):
    html = logged_client_caja.get(f"/clientes/{cliente_test['id_cliente']}").data.decode()
    assert "Total pedidos" in html
    assert "Total gastado" not in html
    assert "Saldo pendiente</div>" not in html


def test_admin_perfil_si_muestra_montos(logged_client, cliente_test, venta_pendiente):
    html = logged_client.get(f"/clientes/{cliente_test['id_cliente']}").data.decode()
    assert "Total gastado" in html
    assert "Saldo pendiente</div>" in html


def test_admin_perfil_muestra_todos_los_pedidos(
    logged_client, cliente_test, venta_pendiente, venta_confeccion
):
    res = logged_client.get(f"/clientes/{cliente_test['id_cliente']}")
    assert _fila_venta(venta_confeccion["id_venta"]) in res.data
    assert _fila_venta(venta_pendiente["id_venta"]) in res.data
    assert b"Exportar Excel" in res.data


# ---------------------------------------------------------------------------
# Cambios y edición
# ---------------------------------------------------------------------------

def test_caja_historial_cambios_cliente(
    logged_client_caja, usuario_caja, db_conn, cliente_test, venta_pendiente
):
    cid = cliente_test["id_cliente"]
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [1])
    assert logged_client_caja.get(f"/clientes/{cid}/historial").status_code == 200
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    assert logged_client_caja.get(f"/clientes/{cid}/historial").status_code == 403


def test_caja_no_puede_editar_cliente_ajeno(
    logged_client_caja, usuario_caja, db_conn, cliente_test, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    logged_client_caja.post("/clientes/guardar", data={
        "id_cliente": str(cliente_test["id_cliente"]),
        "nombre":     "Hackeado",
        "apellido":   "TestApellido",
        "telefono":   "5512345678",
    })
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT nombre FROM cliente WHERE id_cliente = %s", (cliente_test["id_cliente"],))
    assert cursor.fetchone()["nombre"] == "TestNombre"
    cursor.close()


def test_caja_puede_editar_cliente_propio(
    logged_client_caja, usuario_caja, db_conn, cliente_test, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [1])
    logged_client_caja.post("/clientes/guardar", data={
        "id_cliente": str(cliente_test["id_cliente"]),
        "nombre":     "Editado",
        "apellido":   "TestApellido",
        "telefono":   "5512345678",
    })
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT nombre FROM cliente WHERE id_cliente = %s", (cliente_test["id_cliente"],))
    assert cursor.fetchone()["nombre"] == "Editado"
    cursor.close()
