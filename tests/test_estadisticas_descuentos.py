"""
"Total de ventas" (precio antes de descuentos) separado de "Ingresos" (lo cobrado).
Ejemplo del cliente: venta de $100 con $50 de descuento, pagada → vendido $100,
descuentos $50, ingresos $50.
"""
from datetime import date

import pytest

from models.estadisticas import obtener_ventas_brutas, obtener_total_ingresos
from services.estadisticas_service import dashboard_api_service
from services.ventas_service import guardar_venta_service
from tests.conftest import cleanup_venta

HOY = date.today()


def _cifras():
    brutas = obtener_ventas_brutas(HOY, HOY, "1")
    return brutas["total_ventas"], brutas["descuentos"], obtener_total_ingresos(HOY, HOY, "1")


@pytest.fixture
def venta_con_descuento(app, db_conn, usuario_admin, cliente_test, servicio_calzado):
    """Venta de calzado de $100 con $50 de descuento, pagada completa como prepago."""
    form = {
        "id_negocio": "1",
        "id_cliente": str(cliente_test["id_cliente"]),
        "fecha_estimada": "2030-12-31 10:00:00",
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Tenis",
        "articulos[0][marca]": "Nike",
        "articulos[0][material]": "Piel",
        "articulos[0][color_base]": "Blanco",
        "articulos[0][servicios][0][id_servicio]": str(servicio_calzado["id_servicio"]),
        "articulos[0][servicios][0][precio_aplicado]": "100.00",
        "aplica_descuento": "si",
        "cantidad_descuento": "50",
        "prepago": "si",
        "monto_prepago": "50",
        "tipo_pago": "efectivo",
    }
    antes = _cifras()
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])
    assert error is None, error
    yield antes
    cleanup_venta(db_conn, id_venta)


def test_vendido_descuentos_e_ingresos_por_separado(venta_con_descuento):
    vendido_antes, desc_antes, ingresos_antes = venta_con_descuento
    vendido, descuentos, ingresos = _cifras()
    assert vendido    - vendido_antes  == pytest.approx(100)
    assert descuentos - desc_antes     == pytest.approx(50)
    assert ingresos   - ingresos_antes == pytest.approx(50)


def test_api_expone_total_vendido_y_descuentos(venta_con_descuento):
    hoy = HOY.isoformat()
    data, error = dashboard_api_service({"inicio": hoy, "fin": hoy, "id_negocio": "1", "modo": "dia"})
    assert error is None
    k = data["kpis"]
    assert k["total_vendido"] >= 100
    assert k["descuentos"] >= 50
    assert k["total_vendido"] - k["descuentos"] >= 50
    assert {"vendido_pct", "descuentos_pct"} <= set(k)


def test_vendido_por_negocio_es_antes_de_descuentos(venta_con_descuento):
    from models.estadisticas import obtener_ingresos_por_negocio
    vendido_antes = venta_con_descuento[0]
    calzado = next(n for n in obtener_ingresos_por_negocio(HOY, HOY) if n["id_negocio"] == 1)
    assert calzado["total"] == pytest.approx(vendido_antes + 100)


def test_venta_sin_descuento_cuenta_su_total(venta_pendiente):
    # venta_pendiente: $150 sin descuento → suma 150 al vendido y 0 a descuentos
    vendido, descuentos, _ = _cifras()
    assert vendido >= 150
    assert descuentos >= 0


# ── Serie "Total de ventas" ──────────────────────────────────────────────────

@pytest.mark.parametrize("granularidad", ["dia", "semana", "mes"])
def test_serie_vendido_cuadra_con_el_total_de_ventas(venta_con_descuento, granularidad):
    # La suma de la gráfica es el mismo "Total de ventas" del resumen (antes de descuentos)
    from models.estadisticas import obtener_vendido_serie
    serie = obtener_vendido_serie(HOY, HOY, "1", granularidad)
    assert all({"label", "total"} <= set(x) for x in serie)
    assert sum(x["total"] for x in serie) == pytest.approx(_cifras()[0])


def test_serie_vendido_por_hora_cubre_de_7_a_21(venta_con_descuento):
    # Igual que "ventas por hora": fuera de 7:00–21:00 no se grafica
    from models.estadisticas import obtener_vendido_serie
    serie = obtener_vendido_serie(HOY, HOY, "1", "hora")
    assert [x["label"] for x in serie] == [f"{h}:00" for h in range(7, 22)]


def test_api_incluye_serie_vendido(app):
    data, _ = dashboard_api_service({"inicio": f"{HOY.year}-01-01", "fin": f"{HOY.year}-12-31", "modo": "anio"})
    assert len(data["vendido_semanales"]) == 12


def test_exportar_incluye_columna_total_de_ventas(app):
    from services.estadisticas_service import exportar_estadisticas_service
    wb, _ = exportar_estadisticas_service({"inicio": HOY.isoformat(), "fin": HOY.isoformat()})
    ws = wb["Series por período"]
    assert ws.cell(row=3, column=3).value == "Total de ventas ($)"


# ── "Mostrar montos" se reinicia en cada inicio de sesión ────────────────────

def _login(client, usuario):
    client.post("/login?admin=1", data={"usuario": usuario["usuario"], "password": usuario["password"]})
    with client.session_transaction() as sess:
        return sess.get("id_inicio_sesion")


def test_cada_login_genera_un_id_de_sesion_nuevo(app, usuario_admin):
    with app.test_client() as c1, app.test_client() as c2:
        id1, id2 = _login(c1, usuario_admin), _login(c2, usuario_admin)
    assert id1 and id2 and id1 != id2


def test_inicio_lleva_el_id_de_sesion_en_el_boton_de_montos(app, usuario_admin):
    with app.test_client() as c:
        sid  = _login(c, usuario_admin)
        html = c.get("/").data.decode()
    assert f'data-sesion="{sid}"' in html
