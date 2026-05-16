"""
Tests de la capa HTTP — rutas, control de acceso por rol y middleware de sesión.
"""


# ---------------------------------------------------------------------------
# Middleware: sin sesión → redirige al login
# ---------------------------------------------------------------------------

def test_ruta_protegida_sin_sesion_redirige(client):
    res = client.get("/ventas/pendientes")
    assert res.status_code in (302, 401)
    location = res.headers.get("Location", "")
    assert "/login" in location or res.status_code == 401


def test_gastos_sin_sesion_redirige(client):
    res = client.get("/gastos")
    assert res.status_code in (302, 401)


# ---------------------------------------------------------------------------
# Control de acceso por rol: caja no puede ver gastos ni exportar
# ---------------------------------------------------------------------------

def test_gastos_con_rol_caja_retorna_403(logged_client_caja):
    res = logged_client_caja.get("/gastos")
    assert res.status_code == 403


def test_exportar_clientes_con_rol_caja_retorna_403(logged_client_caja):
    res = logged_client_caja.get("/clientes/exportar")
    assert res.status_code == 403


def test_exportar_gastos_con_rol_caja_retorna_403(logged_client_caja):
    res = logged_client_caja.get("/gastos/exportar")
    assert res.status_code == 403


def test_historial_ventas_con_rol_caja_retorna_403(logged_client_caja):
    res = logged_client_caja.get("/ventas/historial")
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Rutas accesibles para admin
# ---------------------------------------------------------------------------

def test_gastos_con_rol_admin_retorna_200(logged_client):
    res = logged_client.get("/gastos")
    assert res.status_code == 200


def test_clientes_con_rol_admin_retorna_200(logged_client):
    res = logged_client.get("/clientes")
    assert res.status_code == 200


def test_ventas_pendientes_con_rol_admin_retorna_200(logged_client):
    res = logged_client.get("/ventas/pendientes")
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Guardar cliente: redirige después de POST
# ---------------------------------------------------------------------------

def test_guardar_cliente_nuevo_redirige(logged_client, db_conn):
    res = logged_client.post("/clientes/guardar", data={
        "nombre": "RutaTest",
        "apellido": "ApellidoRuta",
        "telefono": "5512345699",
        "correo": "",
        "direccion": "",
    }, follow_redirects=False)
    assert res.status_code == 302
    assert "/clientes" in res.headers.get("Location", "")

    # Cleanup
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT id_cliente FROM cliente WHERE nombre='RutaTest' AND apellido='ApellidoRuta'"
    )
    row = cursor.fetchone()
    cursor.close()
    if row:
        cid = row[0]
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM clientes_historial WHERE id_cliente = %s", (cid,))
        cursor.execute("DELETE FROM cliente WHERE id_cliente = %s", (cid,))
        db_conn.commit()
        cursor.close()


# ---------------------------------------------------------------------------
# API clientes: búsqueda
# ---------------------------------------------------------------------------

def test_api_clientes_busqueda_retorna_json(logged_client, cliente_test):
    res = logged_client.get("/api/clientes?q=TestNombre")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    ids = [c["id_cliente"] for c in data]
    assert cliente_test["id_cliente"] in ids


def test_api_clientes_query_vacia_retorna_lista_vacia(logged_client):
    res = logged_client.get("/api/clientes?q=")
    assert res.status_code == 200
    assert res.get_json() == []


# ---------------------------------------------------------------------------
# Ventas: ticket y guardar_venta
# ---------------------------------------------------------------------------

def test_ticket_venta_inexistente_retorna_404(logged_client):
    res = logged_client.get("/ventas/ticket/999999999")
    assert res.status_code == 404


def test_guardar_venta_sin_sesion_retorna_401(client):
    res = client.post("/ventas/guardar", data={"id_negocio": "1"})
    assert res.status_code in (302, 401)


def test_exportar_servicios_con_rol_caja_retorna_403(logged_client_caja):
    res = logged_client_caja.get("/servicios/exportar")
    assert res.status_code == 403


def test_guardar_servicio_con_rol_caja_retorna_403(logged_client_caja):
    res = logged_client_caja.post("/servicios/guardar", data={
        "id_negocio": "1", "nombre": "X", "precio": "10"
    })
    assert res.status_code == 403
