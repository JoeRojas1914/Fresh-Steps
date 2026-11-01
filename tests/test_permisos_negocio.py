"""
Negocios permitidos por usuario de caja (tabla usuario_negocio).

La caja de prueba se limita a Confección (id 2): debe ver venta_confeccion
pero no venta_pendiente (Calzado, id 1), ni poder operar sobre ella.
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


# ---------------------------------------------------------------------------
# Listados
# ---------------------------------------------------------------------------

def test_caja_solo_ve_pendientes_de_sus_negocios(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente, venta_confeccion
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])

    res = logged_client_caja.get(f"/ventas/pendientes?partial=1&id_venta={venta_confeccion['id_venta']}")
    assert _fila_venta(venta_confeccion["id_venta"]) in res.data

    res = logged_client_caja.get(f"/ventas/pendientes?partial=1&id_venta={venta_pendiente['id_venta']}")
    assert _fila_venta(venta_pendiente["id_venta"]) not in res.data


def test_caja_no_puede_forzar_negocio_por_url(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    res = logged_client_caja.get(
        f"/ventas/pendientes?partial=1&id_negocio=1&id_venta={venta_pendiente['id_venta']}"
    )
    assert _fila_venta(venta_pendiente["id_venta"]) not in res.data


def test_caja_sin_negocios_no_ve_ventas(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [])
    res = logged_client_caja.get(f"/ventas/pendientes?partial=1&id_venta={venta_pendiente['id_venta']}")
    assert _fila_venta(venta_pendiente["id_venta"]) not in res.data


def test_admin_ve_todos_los_negocios(logged_client, venta_pendiente, venta_confeccion):
    for v in (venta_pendiente, venta_confeccion):
        res = logged_client.get(f"/ventas/pendientes?partial=1&id_venta={v['id_venta']}")
        assert _fila_venta(v["id_venta"]) in res.data


def test_caja_no_ve_selector_de_negocio(logged_client_caja):
    res = logged_client_caja.get("/ventas/pendientes")
    assert b'id="filtro-negocio"' not in res.data
    res = logged_client_caja.get("/ventas/listas")
    assert b'id="filtro-negocio"' not in res.data


def test_admin_si_ve_selector_de_negocio(logged_client):
    res = logged_client.get("/ventas/pendientes")
    assert b'id="filtro-negocio"' in res.data


# ---------------------------------------------------------------------------
# Acciones sobre una venta de otro negocio
# ---------------------------------------------------------------------------

def test_caja_no_puede_marcar_lista_venta_ajena(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    res = logged_client_caja.post(f"/ventas/marcar-lista/{venta_pendiente['id_venta']}")
    assert res.status_code == 403


def test_caja_no_puede_ver_detalles_ni_ticket_de_venta_ajena(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    assert logged_client_caja.get(f"/ventas/detalles/{venta_pendiente['id_venta']}").status_code == 403
    assert logged_client_caja.get(f"/ventas/ticket/{venta_pendiente['id_venta']}").status_code == 403


def test_caja_no_puede_entregar_ni_cobrar_venta_ajena(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    assert logged_client_caja.post(f"/ventas/entregar/{venta_pendiente['id_venta']}").status_code == 403
    res = logged_client_caja.post("/ventas/pago-final", json={
        "id_venta": venta_pendiente["id_venta"], "monto": "10", "metodo_pago": "efectivo",
    })
    assert res.status_code == 403


def test_caja_si_puede_ver_detalles_de_su_negocio(
    logged_client_caja, usuario_caja, db_conn, venta_confeccion
):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    res = logged_client_caja.get(f"/ventas/detalles/{venta_confeccion['id_venta']}")
    assert res.status_code == 200


def test_caja_no_puede_crear_venta_de_otro_negocio(logged_client_caja, usuario_caja, db_conn):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    res = logged_client_caja.post("/ventas/guardar", data={"id_negocio": "1"})
    assert res.status_code == 403


def test_crear_venta_solo_muestra_negocios_permitidos(logged_client_caja, usuario_caja, db_conn):
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2, 3])
    html = logged_client_caja.get("/ventas").data.decode()
    assert '<option value="1"' not in html
    assert '<option value="2"' in html
    assert '<option value="3"' in html


# ---------------------------------------------------------------------------
# Inicio (KPIs)
# ---------------------------------------------------------------------------

def test_kpis_caja_cuentan_solo_sus_negocios(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente, venta_confeccion
):
    from models.ventas import contar_entregas_resumen
    _asignar_negocios(db_conn, usuario_caja["id_usuario"], [2])
    _, pendientes_confeccion = contar_entregas_resumen(id_negocio=2)

    # Aunque pida "todos", la caja solo recibe lo de sus negocios
    data = logged_client_caja.get("/api/index/kpis?negocio=all").get_json()
    assert data["total_pendientes"] == pendientes_confeccion


def test_index_caja_no_muestra_pastillas_de_negocio(logged_client_caja):
    res = logged_client_caja.get("/")
    assert b"negocio-pills" not in res.data


# ---------------------------------------------------------------------------
# Administración de usuarios
# ---------------------------------------------------------------------------

def test_editar_usuario_guarda_negocios(logged_client, usuario_caja, db_conn):
    res = logged_client.post("/usuarios/guardar", json={
        "id_usuario": str(usuario_caja["id_usuario"]),
        "usuario":    usuario_caja["usuario"],
        "rol":        "caja",
        "negocios":   [1, 2],
    })
    assert res.get_json()["ok"] is True
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT id_negocio FROM usuario_negocio WHERE id_usuario = %s ORDER BY id_negocio",
        (usuario_caja["id_usuario"],),
    )
    assert [r[0] for r in cursor.fetchall()] == [1, 2]
    cursor.close()


def test_crear_usuario_caja_sin_negocios_falla(logged_client):
    res = logged_client.post("/usuarios/guardar", json={
        "usuario":  "sin_negocios_pytest",
        "password": "Segura1x!",
        "rol":      "caja",
        "pin":      "5612",
        "negocios": [],
    })
    data = res.get_json()
    assert data["ok"] is False
    assert "negocio" in data["error"].lower()


def test_editar_usuario_con_negocio_invalido_falla(logged_client, usuario_caja):
    res = logged_client.post("/usuarios/guardar", json={
        "id_usuario": str(usuario_caja["id_usuario"]),
        "usuario":    usuario_caja["usuario"],
        "rol":        "caja",
        "negocios":   [999],
    })
    assert res.get_json()["ok"] is False
