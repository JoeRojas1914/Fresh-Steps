"""
Tests para las mejoras detectadas en el local:
- KPI "ventas cerradas hoy" en el dashboard
- Ordenamiento de todas las tablas por encabezado (construir_order_by + rutas)
- Columna "Fecha de registro" en clientes
"""
from utils import construir_order_by, COLUMNAS_ORDEN_VENTAS
from models.estadisticas_ventas import contar_ventas_entregadas_hoy
from models.clientes import COLUMNAS_ORDEN_CLIENTES
from models.gastos import COLUMNAS_ORDEN_GASTOS
from models.pagos import COLUMNAS_ORDEN_PAGOS
from models.servicios import COLUMNAS_ORDEN_SERVICIOS
from models.usuario import COLUMNAS_ORDEN_USUARIOS
from models.ventas_detalles import COLUMNAS_ORDEN_PEDIDOS_CLIENTE
from models.ventas_historial import COLUMNAS_ORDEN_HISTORIAL



# ---------------------------------------------------------------------------
# construir_order_by
# ---------------------------------------------------------------------------

def test_order_by_columna_valida_asc():
    sql = construir_order_by("fecha_estimada", "asc", "v.id_venta DESC")
    assert sql == " ORDER BY v.fecha_estimada IS NULL, v.fecha_estimada ASC, v.id_venta ASC"


def test_order_by_columna_valida_desc():
    sql = construir_order_by("cliente", "desc", "v.id_venta DESC")
    assert "CONCAT(c.nombre, ' ', c.apellido) DESC" in sql
    assert sql.endswith("v.id_venta DESC")


def test_order_by_sin_orden_usa_default():
    assert construir_order_by(None, None, "v.id_venta DESC") == " ORDER BY v.id_venta DESC"


def test_order_by_columna_invalida_usa_default():
    sql = construir_order_by("v.id_venta; DROP TABLE venta", "asc", "v.id_venta DESC")
    assert sql == " ORDER BY v.id_venta DESC"


def test_order_by_direccion_invalida_es_asc():
    sql = construir_order_by("id", "DESC; DROP TABLE venta", "v.id_venta DESC")
    assert "DROP" not in sql
    assert sql.endswith("v.id_venta ASC")


# ---------------------------------------------------------------------------
# KPI ventas cerradas hoy
# ---------------------------------------------------------------------------

def _set(db_conn, sql, params):
    cursor = db_conn.cursor()
    cursor.execute(sql, params)
    db_conn.commit()
    cursor.close()


def test_ventas_entregadas_hoy_cuenta_y_filtra(app, db_conn, venta_pendiente, venta_confeccion):
    base_all = contar_ventas_entregadas_hoy("all")
    base_1   = contar_ventas_entregadas_hoy("1")
    base_2   = contar_ventas_entregadas_hoy("2")

    # Entregada hoy (calzado, negocio 1)
    _set(db_conn, "UPDATE venta SET fecha_entrega = NOW() WHERE id_venta = %s",
         (venta_pendiente["id_venta"],))
    # Entregada ayer (confección, negocio 2) — no cuenta
    _set(db_conn, "UPDATE venta SET fecha_entrega = NOW() - INTERVAL 1 DAY WHERE id_venta = %s",
         (venta_confeccion["id_venta"],))

    assert contar_ventas_entregadas_hoy("all") == base_all + 1
    assert contar_ventas_entregadas_hoy("1")   == base_1 + 1
    assert contar_ventas_entregadas_hoy("2")   == base_2

    # Eliminada — deja de contar
    _set(db_conn, "UPDATE venta SET eliminado = 1 WHERE id_venta = %s",
         (venta_pendiente["id_venta"],))
    assert contar_ventas_entregadas_hoy("all") == base_all


def test_api_index_kpis_incluye_ventas_entregadas_hoy(logged_client):
    resp = logged_client.get("/api/index/kpis?negocio=all")
    assert resp.status_code == 200
    assert "ventas_entregadas_hoy" in resp.get_json()


def test_index_muestra_kpi_ventas_cerradas(logged_client):
    resp = logged_client.get("/")
    assert resp.status_code == 200
    assert "Ventas cerradas hoy".encode() in resp.data


# ---------------------------------------------------------------------------
# Ordenamiento en tablas
# ---------------------------------------------------------------------------

def _pos(html: bytes, id_venta: int) -> int:
    return html.index(f"#{id_venta}</td>".encode())


def test_pendientes_ordena_por_fecha_estimada(logged_client, db_conn, venta_pendiente, venta_confeccion):
    id_a, id_b = venta_pendiente["id_venta"], venta_confeccion["id_venta"]
    _set(db_conn, "UPDATE venta SET fecha_estimada = '2030-12-01 10:00:00' WHERE id_venta = %s", (id_a,))
    _set(db_conn, "UPDATE venta SET fecha_estimada = '2030-12-20 10:00:00' WHERE id_venta = %s", (id_b,))

    url = "/ventas/pendientes?partial=1&q=TestNombre&orden=fecha_estimada&dir="
    asc  = logged_client.get(url + "asc")
    desc = logged_client.get(url + "desc")
    assert asc.status_code == desc.status_code == 200
    assert _pos(asc.data, id_a)  < _pos(asc.data, id_b)
    assert _pos(desc.data, id_b) < _pos(desc.data, id_a)
    assert b'th-sort is-asc' in asc.data
    assert b'th-sort is-desc' in desc.data


def test_listas_ordena_por_recibo(logged_client, db_conn, venta_pendiente, venta_confeccion):
    id_a, id_b = sorted([venta_pendiente["id_venta"], venta_confeccion["id_venta"]])
    _set(db_conn, "UPDATE venta SET fecha_lista = NOW() WHERE id_venta IN (%s, %s)", (id_a, id_b))

    desc = logged_client.get("/ventas/listas?partial=1&q=TestNombre&orden=id&dir=desc")
    assert desc.status_code == 200
    assert _pos(desc.data, id_b) < _pos(desc.data, id_a)


def test_historial_fecha_entrega_nulls_al_final(logged_client, db_conn, venta_pendiente, venta_confeccion):
    id_entregada, id_pendiente = venta_pendiente["id_venta"], venta_confeccion["id_venta"]
    _set(db_conn, "UPDATE venta SET fecha_lista = NOW(), fecha_entrega = NOW() WHERE id_venta = %s",
         (id_entregada,))

    for direccion in ("asc", "desc"):
        resp = logged_client.get(
            f"/ventas/historial?partial=1&q=TestNombre&orden=fecha_entrega&dir={direccion}"
        )
        assert resp.status_code == 200
        assert _pos(resp.data, id_entregada) < _pos(resp.data, id_pendiente)


def test_orden_invalido_no_rompe(logged_client):
    resp = logged_client.get("/ventas/historial?partial=1&orden=nope&dir=zzz")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Todas las tablas: cada columna ordenable genera SQL válido en ambas direcciones
# ---------------------------------------------------------------------------

# Pendientes y Listas no muestran fecha lista / fecha entrega como columna
_SIN_FECHAS_CIERRE = {k for k in COLUMNAS_ORDEN_VENTAS if k not in ("fecha_lista", "fecha_entrega")}

# (url, columnas permitidas en SQL, columnas con encabezado visible)
_TABLAS = [
    ("/usuarios",          COLUMNAS_ORDEN_USUARIOS,  COLUMNAS_ORDEN_USUARIOS),
    ("/servicios",         COLUMNAS_ORDEN_SERVICIOS, COLUMNAS_ORDEN_SERVICIOS),
    ("/gastos",            COLUMNAS_ORDEN_GASTOS,    COLUMNAS_ORDEN_GASTOS),
    ("/pagos",             COLUMNAS_ORDEN_PAGOS,     COLUMNAS_ORDEN_PAGOS),
    ("/clientes",          COLUMNAS_ORDEN_CLIENTES,  COLUMNAS_ORDEN_CLIENTES),
    ("/ventas/pendientes", COLUMNAS_ORDEN_VENTAS,    _SIN_FECHAS_CIERRE),
    ("/ventas/listas",     COLUMNAS_ORDEN_VENTAS,    _SIN_FECHAS_CIERRE),
    ("/ventas/historial",  COLUMNAS_ORDEN_HISTORIAL, COLUMNAS_ORDEN_HISTORIAL),
]


def test_todas_las_columnas_ordenables_responden_200(logged_client, venta_pendiente, gasto_test):
    for url, columnas, visibles in _TABLAS:
        for clave in columnas:
            for direccion in ("asc", "desc"):
                resp = logged_client.get(f"{url}?partial=1&orden={clave}&dir={direccion}")
                assert resp.status_code == 200, (url, clave, direccion)
        for clave in visibles:
            assert f'data-sort="{clave}"'.encode() in resp.data, (url, clave)


def test_pedidos_cliente_columnas_ordenables(logged_client, cliente_test, venta_pendiente):
    url = f"/clientes/{cliente_test['id_cliente']}"
    for clave in COLUMNAS_ORDEN_PEDIDOS_CLIENTE:
        for direccion in ("asc", "desc"):
            resp = logged_client.get(f"{url}?partial=1&orden={clave}&dir={direccion}")
            assert resp.status_code == 200, (clave, direccion)


def test_clientes_muestra_fecha_registro(logged_client, cliente_test):
    resp = logged_client.get("/clientes?partial=1&q=TestNombre")
    assert resp.status_code == 200
    assert "Fecha de registro".encode() in resp.data


def test_clientes_ordena_por_fecha_registro(logged_client, db_conn, cliente_test, usuario_admin):
    cursor = db_conn.cursor()
    cursor.execute(
        """INSERT INTO cliente (nombre, apellido, telefono, activo, id_usuario, fecha_registro)
           VALUES ('TestNombre', 'Antiguo', '5500000001', 1, %s, '2020-01-01 09:00:00')""",
        (usuario_admin["id_usuario"],),
    )
    db_conn.commit()
    id_antiguo = cursor.lastrowid
    try:
        resp = logged_client.get("/clientes?partial=1&q=TestNombre&orden=fecha_registro&dir=asc")
        html = resp.data
        assert html.index(b"01/01/2020") < html.index(b"TestApellido")
    finally:
        cursor.execute("DELETE FROM clientes_historial WHERE id_cliente = %s", (id_antiguo,))
        cursor.execute("DELETE FROM cliente WHERE id_cliente = %s", (id_antiguo,))
        db_conn.commit()
        cursor.close()


def test_historial_ordena_por_estado(logged_client, db_conn, venta_pendiente, venta_confeccion):
    id_pendiente, id_entregada = venta_pendiente["id_venta"], venta_confeccion["id_venta"]
    _set(db_conn, "UPDATE venta SET fecha_lista = NOW(), fecha_entrega = NOW() WHERE id_venta = %s",
         (id_entregada,))

    url = "/ventas/historial?partial=1&q=TestNombre&orden=estado&dir="
    asc  = logged_client.get(url + "asc").data
    desc = logged_client.get(url + "desc").data
    assert _pos(asc, id_pendiente)  < _pos(asc, id_entregada)
    assert _pos(desc, id_entregada) < _pos(desc, id_pendiente)
