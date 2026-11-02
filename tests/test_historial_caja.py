"""
Historial de ventas para usuarios de caja.

La caja puede consultar el historial, pero solo de sus negocios asignados,
sin ventas eliminadas y sin exportar a Excel.
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


def _fila_venta(id_venta):
    return f'id="detalles-{id_venta}"'.encode()


def _eliminar(app, id_venta, id_usuario):
    from services.ventas_service import eliminar_venta_service
    with app.test_request_context("/"):
        eliminar_venta_service(id_venta, id_usuario)


# ---------------------------------------------------------------------------
# Acceso
# ---------------------------------------------------------------------------

def test_caja_puede_abrir_historial(logged_client_caja):
    res = logged_client_caja.get("/ventas/historial")
    assert res.status_code == 200
    assert b'id="form-filtro-historial"' in res.data


def test_caja_ve_enlace_historial_en_menu(logged_client_caja):
    res = logged_client_caja.get("/ventas/pendientes")
    assert b'href="/ventas/historial"' in res.data


def test_caja_no_puede_exportar_historial(logged_client_caja):
    assert logged_client_caja.get("/ventas/historial/exportar").status_code == 403


def test_caja_no_ve_boton_exportar_ni_eliminadas(logged_client_caja):
    html = logged_client_caja.get("/ventas/historial").data.decode()
    assert "Exportar Excel" not in html
    assert 'name="eliminadas"' not in html
    assert 'value="eliminada"' not in html


def test_admin_sigue_viendo_exportar_y_eliminadas(logged_client):
    html = logged_client.get("/ventas/historial").data.decode()
    assert "Exportar Excel" in html
    assert 'name="eliminadas"' in html
    assert 'value="eliminada"' in html


# ---------------------------------------------------------------------------
# Negocios
# ---------------------------------------------------------------------------

def test_caja_solo_ve_historial_de_sus_negocios(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente, venta_confeccion
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])

    res = logged_client_caja.get(f"/ventas/historial?partial=1&id_venta={venta_confeccion['id_venta']}")
    assert _fila_venta(venta_confeccion["id_venta"]) in res.data

    res = logged_client_caja.get(f"/ventas/historial?partial=1&id_venta={venta_pendiente['id_venta']}")
    assert _fila_venta(venta_pendiente["id_venta"]) not in res.data


def test_caja_no_puede_forzar_otro_negocio_en_historial(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    res = logged_client_caja.get(
        f"/ventas/historial?partial=1&id_negocio=1&id_venta={venta_pendiente['id_venta']}"
    )
    assert _fila_venta(venta_pendiente["id_venta"]) not in res.data


def test_caja_con_un_negocio_no_ve_selector(logged_client_caja, usuario_caja, db_conn):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    html = logged_client_caja.get("/ventas/historial").data.decode()
    assert 'name="id_negocio"' not in html


def test_caja_con_varios_negocios_solo_ve_los_suyos(logged_client_caja, usuario_caja, db_conn):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2, 3])
    html = logged_client_caja.get("/ventas/historial").data.decode()
    assert 'name="id_negocio" value="1"' not in html
    assert 'name="id_negocio" value="2"' in html
    assert 'name="id_negocio" value="3"' in html


def test_caja_no_ve_cambios_de_venta_ajena(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    res = logged_client_caja.get(f"/ventas/{venta_pendiente['id_venta']}/historial")
    assert res.status_code == 403


def test_caja_si_ve_cambios_de_venta_propia(
    logged_client_caja, usuario_caja, db_conn, venta_confeccion
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    res = logged_client_caja.get(f"/ventas/{venta_confeccion['id_venta']}/historial")
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Ventas eliminadas
# ---------------------------------------------------------------------------

def test_caja_no_ve_eliminadas_aunque_lo_pida(
    app, logged_client_caja, usuario_admin, venta_pendiente
):
    id_venta = venta_pendiente["id_venta"]
    _eliminar(app, id_venta, usuario_admin["id_usuario"])

    for qs in ("eliminadas=1", "estado=eliminada", "eliminadas=1&estado=eliminada"):
        res = logged_client_caja.get(f"/ventas/historial?partial=1&id_venta={id_venta}&{qs}")
        assert res.status_code == 200
        assert _fila_venta(id_venta) not in res.data, qs


def test_admin_si_ve_eliminadas(app, logged_client, usuario_admin, venta_pendiente):
    id_venta = venta_pendiente["id_venta"]
    _eliminar(app, id_venta, usuario_admin["id_usuario"])
    res = logged_client.get(f"/ventas/historial?partial=1&id_venta={id_venta}&estado=eliminada")
    assert _fila_venta(id_venta) in res.data


def test_caja_no_ve_cambios_de_venta_eliminada(
    app, logged_client_caja, usuario_admin, venta_pendiente
):
    id_venta = venta_pendiente["id_venta"]
    _eliminar(app, id_venta, usuario_admin["id_usuario"])
    assert logged_client_caja.get(f"/ventas/{id_venta}/historial").status_code == 403
