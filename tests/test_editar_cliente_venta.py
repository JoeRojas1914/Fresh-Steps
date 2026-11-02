"""
Edición rápida del cliente seleccionado en "Nueva venta"
(/api/clientes/<id> y /api/clientes/<id>/editar).
"""


def _datos(**extra):
    datos = {
        "nombre":    "Editado",
        "apellido":  "Pytest",
        "telefono":  "5512345678",
        "correo":    "editado@test.com",
        "direccion": "06600",
    }
    datos.update(extra)
    return datos


def test_obtener_cliente_devuelve_datos_editables(logged_client, cliente_test):
    res = logged_client.get(f"/api/clientes/{cliente_test['id_cliente']}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["id_cliente"] == cliente_test["id_cliente"]
    assert data["nombre"] == "TestNombre"
    assert set(data) >= {"telefono", "correo", "direccion"}


def test_obtener_cliente_inexistente_404(logged_client):
    assert logged_client.get("/api/clientes/999999999").status_code == 404


def test_editar_cliente_guarda_cambios(logged_client, cliente_test, db_conn):
    id_cliente = cliente_test["id_cliente"]
    res = logged_client.post(f"/api/clientes/{id_cliente}/editar", data=_datos())
    data = res.get_json()
    assert res.status_code == 200 and data["ok"] is True
    assert data["cliente"]["nombre"] == "Editado"

    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT nombre, correo, direccion FROM cliente WHERE id_cliente = %s", (id_cliente,))
    row = cursor.fetchone()
    cursor.close()
    assert row == {"nombre": "Editado", "correo": "editado@test.com", "direccion": "06600"}


def test_editar_cliente_telefono_invalido_400(logged_client, cliente_test):
    res = logged_client.post(
        f"/api/clientes/{cliente_test['id_cliente']}/editar", data=_datos(telefono="123")
    )
    assert res.status_code == 400
    assert res.get_json()["ok"] is False


def test_editar_cliente_inexistente_404(logged_client):
    assert logged_client.post("/api/clientes/999999999/editar", data=_datos()).status_code == 404


def test_caja_puede_editar_cliente_desde_venta(logged_client_caja, cliente_test):
    res = logged_client_caja.post(f"/api/clientes/{cliente_test['id_cliente']}/editar", data=_datos())
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_pagina_nueva_venta_tiene_boton_y_modal(logged_client):
    html = logged_client.get("/ventas").data.decode()
    assert 'id="btn-editar-cliente"' in html
    assert 'id="formEditarCliente"' in html
