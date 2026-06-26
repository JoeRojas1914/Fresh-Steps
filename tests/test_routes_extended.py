"""
Tests HTTP extendidos — GET/POST en rutas de gastos, servicios, clientes,
pagos, estadísticas y usuarios. Cada test verifica status code y, donde
corresponde, el Content-Type de la respuesta.
"""
import pytest

XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


# ===========================================================================
# GASTOS
# ===========================================================================

def test_gastos_lista_200(logged_client):
    res = logged_client.get("/gastos")
    assert res.status_code == 200


def test_gastos_lista_con_filtros_200(logged_client):
    res = logged_client.get("/gastos?id_negocio=1&pagina=1")
    assert res.status_code == 200


def test_gastos_lista_partial_200(logged_client):
    res = logged_client.get("/gastos?partial=1")
    assert res.status_code == 200


def test_guardar_gasto_nuevo_redirige(logged_client, usuario_admin, db_conn):
    res = logged_client.post("/gastos/guardar", data={
        "id_negocio":       "1",
        "id_categoria":     "",
        "descripcion":      "GastoRutaTest",
        "proveedor":        "ProvTest",
        "total":            "99.50",
        "fecha_registro":   "2030-01-01",
        "tipo_comprobante": "ticket",
        "tipo_pago":        "efectivo",
        "notas":            "",
    }, follow_redirects=False)
    assert res.status_code == 302

    cursor = db_conn.cursor()
    cursor.execute("SELECT id_gasto FROM gastos WHERE descripcion='GastoRutaTest'")
    row = cursor.fetchone()
    cursor.close()
    if row:
        gid = row[0]
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM gastos_historial WHERE id_gasto=%s", (gid,))
        cursor.execute("DELETE FROM gastos WHERE id_gasto=%s", (gid,))
        db_conn.commit()
        cursor.close()


def test_eliminar_gasto_redirige(logged_client, gasto_test):
    res = logged_client.post(f"/gastos/eliminar/{gasto_test['id_gasto']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_restaurar_gasto_redirige(logged_client, gasto_test, usuario_admin, db_conn):
    from services.gastos_service import eliminar_gasto_service
    eliminar_gasto_service(gasto_test["id_gasto"], usuario_admin["id_usuario"])
    res = logged_client.post(f"/gastos/restaurar/{gasto_test['id_gasto']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_historial_gasto_retorna_json(logged_client, gasto_test):
    res = logged_client.get(f"/gastos/{gasto_test['id_gasto']}/historial")
    assert res.status_code == 200
    assert res.is_json


def test_guardar_categoria_nueva(logged_client):
    res = logged_client.post(
        "/gastos/categorias/guardar",
        json={"nombre": "CatRutaTest"},
    )
    assert res.status_code == 200
    assert res.get_json()["ok"] is True

    # Cleanup
    from models.gastos import obtener_categorias, eliminar_categoria
    cats = obtener_categorias()
    for c in cats:
        if c["nombre"] == "CatRutaTest":
            from db import get_db
            with get_db() as (_, cur):
                cur.execute("DELETE FROM categoria_gasto WHERE id_categoria=%s", (c["id_categoria"],))
            break


def test_guardar_categoria_nombre_vacio_retorna_400(logged_client):
    res = logged_client.post("/gastos/categorias/guardar", json={"nombre": ""})
    assert res.status_code == 400


def test_exportar_gastos_retorna_xlsx(logged_client):
    res = logged_client.get("/gastos/exportar")
    assert res.status_code == 200
    assert XLSX_CONTENT_TYPE in res.content_type


# ===========================================================================
# SERVICIOS
# ===========================================================================

def test_servicios_lista_200(logged_client):
    res = logged_client.get("/servicios")
    assert res.status_code == 200


def test_servicios_lista_con_busqueda_200(logged_client):
    res = logged_client.get("/servicios?q=Limpieza&id_negocio=1")
    assert res.status_code == 200


def test_servicios_lista_partial_200(logged_client):
    res = logged_client.get("/servicios?partial=1")
    assert res.status_code == 200


def test_guardar_servicio_nuevo_redirige(logged_client, db_conn):
    res = logged_client.post("/servicios/guardar", data={
        "id_negocio": "1",
        "nombre":     "ServRutaTest",
        "precio":     "80.00",
    }, follow_redirects=False)
    assert res.status_code == 302

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT id_servicio FROM servicio WHERE nombre='ServRutaTest' AND id_negocio=1"
    )
    row = cursor.fetchone()
    cursor.close()
    if row:
        sid = row[0]
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM servicios_historial WHERE id_servicio=%s", (sid,))
        cursor.execute("DELETE FROM servicio WHERE id_servicio=%s", (sid,))
        db_conn.commit()
        cursor.close()


def test_eliminar_servicio_redirige(logged_client, servicio_calzado):
    res = logged_client.post(f"/servicios/eliminar/{servicio_calzado['id_servicio']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_restaurar_servicio_redirige(logged_client, servicio_calzado, usuario_admin):
    from services.servicios_service import eliminar_servicio_service
    eliminar_servicio_service(servicio_calzado["id_servicio"], usuario_admin["id_usuario"])
    res = logged_client.post(f"/servicios/restaurar/{servicio_calzado['id_servicio']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_api_servicios_retorna_lista(logged_client, servicio_calzado):
    res = logged_client.get("/api/servicios?id_negocio=1")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)


def test_historial_servicio_retorna_json(logged_client, servicio_calzado):
    res = logged_client.get(f"/servicios/{servicio_calzado['id_servicio']}/historial")
    assert res.status_code == 200
    assert res.is_json


def test_exportar_servicios_retorna_xlsx(logged_client):
    res = logged_client.get("/servicios/exportar")
    assert res.status_code == 200
    assert XLSX_CONTENT_TYPE in res.content_type


# ===========================================================================
# CLIENTES
# ===========================================================================

def test_clientes_lista_200(logged_client):
    res = logged_client.get("/clientes")
    assert res.status_code == 200


def test_clientes_lista_partial_200(logged_client):
    res = logged_client.get("/clientes?partial=1")
    assert res.status_code == 200


def test_eliminar_cliente_redirige(logged_client, cliente_test):
    res = logged_client.post(f"/clientes/eliminar/{cliente_test['id_cliente']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_restaurar_cliente_redirige(logged_client, cliente_test, usuario_admin):
    from services.clientes_service import eliminar_cliente_service
    eliminar_cliente_service(cliente_test["id_cliente"], id_usuario=usuario_admin["id_usuario"])
    res = logged_client.post(f"/clientes/restaurar/{cliente_test['id_cliente']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_historial_cliente_retorna_json(logged_client, cliente_test):
    res = logged_client.get(f"/clientes/{cliente_test['id_cliente']}/historial")
    assert res.status_code == 200
    assert res.is_json


def test_ver_cliente_200(logged_client, cliente_test):
    res = logged_client.get(f"/clientes/{cliente_test['id_cliente']}")
    assert res.status_code == 200


def test_exportar_clientes_retorna_xlsx(logged_client):
    res = logged_client.get("/clientes/exportar")
    assert res.status_code == 200
    assert XLSX_CONTENT_TYPE in res.content_type


def test_exportar_cliente_individual_retorna_xlsx(logged_client, cliente_test):
    res = logged_client.get(f"/clientes/{cliente_test['id_cliente']}/exportar")
    assert res.status_code == 200
    assert XLSX_CONTENT_TYPE in res.content_type


def test_api_crear_cliente_retorna_json(logged_client, db_conn):
    res = logged_client.post("/api/clientes/crear", data={
        "nombre":    "ApiRuta",
        "apellido":  "TestCli",
        "telefono":  "5500000001",
        "correo":    "",
        "direccion": "",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "id_cliente" in data

    cid = data["id_cliente"]
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM clientes_historial WHERE id_cliente=%s", (cid,))
    cursor.execute("DELETE FROM cliente WHERE id_cliente=%s", (cid,))
    db_conn.commit()
    cursor.close()


# ===========================================================================
# PAGOS
# ===========================================================================

def test_historial_pagos_200(logged_client):
    res = logged_client.get("/pagos")
    assert res.status_code == 200


def test_historial_pagos_partial_200(logged_client):
    res = logged_client.get("/pagos?partial=1")
    assert res.status_code == 200


def test_exportar_pagos_retorna_xlsx(logged_client):
    res = logged_client.get("/pagos/exportar-excel")
    assert res.status_code == 200
    assert XLSX_CONTENT_TYPE in res.content_type


# ===========================================================================
# ESTADÍSTICAS
# ===========================================================================

def test_estadisticas_200(logged_client):
    res = logged_client.get("/estadisticas")
    assert res.status_code == 200


def test_exportar_estadisticas_sin_fechas_400(logged_client):
    res = logged_client.get("/estadisticas/exportar")
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_exportar_estadisticas_con_fechas_xlsx(logged_client):
    res = logged_client.get("/estadisticas/exportar?inicio=2026-06-01&fin=2026-06-30")
    assert res.status_code == 200
    assert XLSX_CONTENT_TYPE in res.content_type


def test_api_dashboard_sin_fechas_400(logged_client):
    res = logged_client.get("/api/estadisticas/dashboard")
    assert res.status_code == 400


def test_api_dashboard_con_fechas_200(logged_client):
    res = logged_client.get(
        "/api/estadisticas/dashboard?inicio=2026-06-01&fin=2026-06-30"
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "kpis" in data


# ===========================================================================
# USUARIOS
# ===========================================================================

def test_listar_usuarios_200(logged_client):
    res = logged_client.get("/usuarios")
    assert res.status_code == 200


def test_listar_usuarios_partial_200(logged_client):
    res = logged_client.get("/usuarios?partial=1")
    assert res.status_code == 200


def test_guardar_usuario_nuevo_retorna_json(logged_client, db_conn):
    res = logged_client.post("/usuarios/guardar", json={
        "usuario":  "ruta_test_usr",
        "password": "Segura1x",
        "rol":      "caja",
        "pin":      "4321",
        "nombre":   "Ruta",
        "apellido": "Test",
    })
    assert res.status_code == 200
    assert res.get_json()["ok"] is True

    cursor = db_conn.cursor()
    cursor.execute("SELECT id_usuario FROM usuario WHERE usuario='ruta_test_usr'")
    row = cursor.fetchone()
    cursor.close()
    if row:
        uid = row[0]
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM historial_usuario WHERE id_usuario=%s", (uid,))
        cursor.execute("DELETE FROM login_log WHERE id_usuario=%s", (uid,))
        cursor.execute("DELETE FROM usuario WHERE id_usuario=%s", (uid,))
        db_conn.commit()
        cursor.close()


def test_toggle_usuario_redirige(logged_client, usuario_caja):
    res = logged_client.post(f"/usuarios/toggle/{usuario_caja['id_usuario']}")
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_historial_usuario_retorna_json(logged_client, usuario_admin):
    res = logged_client.get(f"/usuarios/{usuario_admin['id_usuario']}/historial")
    assert res.status_code == 200
    assert res.is_json


def test_exportar_cliente_con_ventas_xlsx(logged_client, cliente_test, venta_pendiente):
    """Cubre excel_helpers.py _build_ws_resumen/_ws_articulos/_ws_pagos loop bodies."""
    # venta_pendiente crea una venta para cliente_test en DB → Excel incluye pedidos
    assert venta_pendiente["id_venta"] is not None
    res = logged_client.get(f"/clientes/{cliente_test['id_cliente']}/exportar")
    assert res.status_code == 200
    assert XLSX_CONTENT_TYPE in res.content_type


def test_mi_perfil_200(logged_client):
    res = logged_client.get("/mi-perfil")
    assert res.status_code == 200


# ===========================================================================
# INDEX / HEALTH
# ===========================================================================

def test_index_con_sesion_200(logged_client):
    res = logged_client.get("/")
    assert res.status_code == 200


def test_api_index_kpis_200(logged_client):
    res = logged_client.get("/api/index/kpis")
    assert res.status_code == 200
    data = res.get_json()
    assert "ventas_hoy" in data


def test_health_ok(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
