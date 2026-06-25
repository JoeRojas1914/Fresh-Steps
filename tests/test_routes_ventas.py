"""
Tests HTTP para routes/ventas_routes.py.
Cubre: lista, pendientes, historial, ticket, detalles, guardar,
       marcar-lista, revertir, entregar, pago-final, eliminar,
       editar GET/POST, exportar Excel, abrir-whatsapp.
"""
import pytest
from tests.conftest import cleanup_venta

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FECHA = "2030-12-31 10:00:00"


# ===========================================================================
# Páginas de listado
# ===========================================================================

def test_ventas_crear_200(logged_client):
    res = logged_client.get("/ventas")
    assert res.status_code == 200


def test_ventas_listas_200(logged_client):
    res = logged_client.get("/ventas/listas")
    assert res.status_code == 200


def test_ventas_listas_partial_200(logged_client):
    res = logged_client.get("/ventas/listas?partial=1")
    assert res.status_code == 200


def test_ventas_listas_filtros_200(logged_client):
    res = logged_client.get("/ventas/listas?id_negocio=1&pagina=1&q=test")
    assert res.status_code == 200


def test_ventas_pendientes_200(logged_client):
    res = logged_client.get("/ventas/pendientes")
    assert res.status_code == 200


def test_ventas_pendientes_partial_200(logged_client):
    res = logged_client.get("/ventas/pendientes?partial=1")
    assert res.status_code == 200


def test_historial_ventas_200(logged_client):
    res = logged_client.get("/ventas/historial")
    assert res.status_code == 200


def test_historial_ventas_partial_200(logged_client):
    res = logged_client.get("/ventas/historial?partial=1")
    assert res.status_code == 200


def test_historial_ventas_con_filtros_200(logged_client):
    res = logged_client.get(
        "/ventas/historial?id_negocio=1&fecha_inicio=2026-01-01&fecha_fin=2026-12-31"
        "&estado=Entregada&tipo_fecha=fecha_entrega&eliminadas=1"
    )
    assert res.status_code == 200


def test_historial_ventas_exportar_xlsx(logged_client):
    res = logged_client.get("/ventas/historial/exportar")
    assert res.status_code == 200
    assert XLSX_CONTENT_TYPE in res.content_type


# ===========================================================================
# Ticket y detalles (necesitan venta existente)
# ===========================================================================

def test_venta_ticket_200(logged_client, venta_pendiente):
    res = logged_client.get(f"/ventas/ticket/{venta_pendiente['id_venta']}")
    assert res.status_code == 200


def test_venta_ticket_con_copias_200(logged_client, venta_pendiente):
    res = logged_client.get(f"/ventas/ticket/{venta_pendiente['id_venta']}?copias=2")
    assert res.status_code == 200


def test_venta_ticket_inexistente_404(logged_client):
    res = logged_client.get("/ventas/ticket/999999")
    assert res.status_code == 404


def test_detalles_venta_retorna_json(logged_client, venta_pendiente):
    res = logged_client.get(f"/ventas/detalles/{venta_pendiente['id_venta']}")
    assert res.status_code == 200
    assert res.is_json
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_historial_venta_retorna_json(logged_client, venta_pendiente):
    res = logged_client.get(f"/ventas/{venta_pendiente['id_venta']}/historial")
    assert res.status_code == 200
    assert res.is_json


# ===========================================================================
# Guardar venta (POST)
# ===========================================================================

def test_guardar_venta_sin_datos_400(logged_client):
    res = logged_client.post("/ventas/guardar", data={"id_negocio": "no_es_numero"})
    assert res.status_code == 400
    assert res.get_json()["ok"] is False


def test_guardar_venta_sin_cliente_400(logged_client):
    res = logged_client.post("/ventas/guardar", data={
        "id_negocio": "3",
        "fecha_estimada": FECHA,
        "articulos[0][tipo_articulo]": "maquila",
        "articulos[0][tipo]": "Mandil",
        "articulos[0][cantidad]": "1",
        "articulos[0][precio_unitario]": "50.00",
    })
    assert res.status_code == 400


def test_guardar_venta_valida_crea_201(logged_client, db_conn, cliente_test, servicio_calzado, usuario_admin):
    sid = servicio_calzado["id_servicio"]
    res = logged_client.post("/ventas/guardar", data={
        "id_negocio": "1",
        "id_cliente": str(cliente_test["id_cliente"]),
        "fecha_estimada": FECHA,
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Bota",
        "articulos[0][marca]": "Skechers",
        "articulos[0][material]": "Cuero",
        "articulos[0][color_base]": "Negro",
        f"articulos[0][servicios][0][id_servicio]": str(sid),
        f"articulos[0][servicios][0][precio_aplicado]": "150.00",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    id_venta = data["id_venta"]
    cleanup_venta(db_conn, id_venta)


# ===========================================================================
# Marcar lista / revertir
# ===========================================================================

def test_marcar_lista_200(logged_client, venta_pendiente):
    res = logged_client.post(f"/ventas/marcar-lista/{venta_pendiente['id_venta']}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True


def test_revertir_lista_200(logged_client, venta_pendiente, usuario_admin):
    # Primero marcamos como lista
    from services.ventas_service import marcar_lista_service
    marcar_lista_service(venta_pendiente["id_venta"], usuario_admin["id_usuario"])
    # Luego revertimos via ruta
    res = logged_client.post(f"/ventas/revertir-lista/{venta_pendiente['id_venta']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_revertir_lista_pendiente_devuelve_false(logged_client, venta_pendiente):
    res = logged_client.post(f"/ventas/revertir-lista/{venta_pendiente['id_venta']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is False


# ===========================================================================
# Pago final / entregar
# ===========================================================================

def test_pago_final_sin_datos_400(logged_client):
    res = logged_client.post("/ventas/pago-final", json={})
    assert res.status_code == 400
    assert res.get_json()["ok"] is False


def test_pago_final_metodo_invalido_400(logged_client, venta_pendiente):
    res = logged_client.post("/ventas/pago-final", json={
        "id_venta": venta_pendiente["id_venta"],
        "monto": "150.00",
        "metodo_pago": "cripto",
    })
    assert res.status_code == 400


def test_pago_final_valido_200(logged_client, venta_pendiente):
    res = logged_client.post("/ventas/pago-final", json={
        "id_venta": venta_pendiente["id_venta"],
        "monto": "150.00",
        "metodo_pago": "efectivo",
    })
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_entregar_venta_200(logged_client, venta_pendiente):
    res = logged_client.post(f"/ventas/entregar/{venta_pendiente['id_venta']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


# ===========================================================================
# Eliminar venta
# ===========================================================================

def test_eliminar_venta_200(logged_client, venta_pendiente):
    res = logged_client.post(f"/ventas/eliminar/{venta_pendiente['id_venta']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_eliminar_venta_inexistente_400(logged_client):
    res = logged_client.post("/ventas/eliminar/999999")
    assert res.status_code == 400


# ===========================================================================
# Editar venta (GET + POST)
# ===========================================================================

def test_editar_venta_get_200(logged_client, venta_pendiente):
    res = logged_client.get(f"/ventas/pendientes/{venta_pendiente['id_venta']}/editar")
    assert res.status_code == 200


def test_editar_venta_get_404(logged_client):
    res = logged_client.get("/ventas/pendientes/999999/editar")
    assert res.status_code == 404


def test_editar_venta_post_sin_cambios_400(logged_client, venta_pendiente):
    res = logged_client.post(
        f"/ventas/pendientes/{venta_pendiente['id_venta']}/editar",
        data={},
    )
    assert res.status_code == 400
    assert res.get_json()["ok"] is False


def test_editar_venta_post_cambia_fecha_200(logged_client, venta_pendiente):
    res = logged_client.post(
        f"/ventas/pendientes/{venta_pendiente['id_venta']}/editar",
        data={
            "fecha_estimada_fecha": "2031-06-15",
            "fecha_estimada_hora": "14:30",
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert "total_nuevo" in data


# ===========================================================================
# WhatsApp
# ===========================================================================

def test_abrir_whatsapp_url_invalida_400(logged_client):
    res = logged_client.post("/ventas/abrir-whatsapp", json={
        "url": "https://evil.com/xss",
        "negocio_id": 1,
    })
    assert res.status_code == 400
    assert res.get_json()["ok"] is False


def test_abrir_whatsapp_url_valida_200(logged_client):
    res = logged_client.post("/ventas/abrir-whatsapp", json={
        "url": "https://web.whatsapp.com/send?phone=521234567890&text=hola",
        "negocio_id": 1,
    }, headers={"X-Forwarded-For": "1.2.3.4"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert data.get("opened") is False
    assert "url" in data
