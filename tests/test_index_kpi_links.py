"""
Los KPIs del día en el inicio son enlaces al historial con el filtro de hoy.
"""
import re
from datetime import date

from models.ventas_historial import contar_historial_ventas

HOY = date.today().isoformat()


def _href(html, data_kpi):
    """href del <a> que contiene el número con ese data-kpi."""
    m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>(?:(?!</a>).)*data-kpi="' + data_kpi + '"', html, re.S)
    assert m, f"KPI {data_kpi} no es un enlace"
    return m.group(1).replace("&amp;", "&")


def test_kpis_de_recibo_llevan_al_historial_de_hoy(logged_client):
    html = logged_client.get("/").data.decode()
    for kpi in ("ventas_hoy", "unidades_recibidas"):
        url = _href(html, kpi)
        assert url.startswith("/ventas/historial?")
        assert "tipo_fecha=fecha_recibo" in url
        assert f"fecha_inicio={HOY}" in url and f"fecha_fin={HOY}" in url


def test_kpis_de_entrega_llevan_al_historial_de_hoy(logged_client):
    html = logged_client.get("/").data.decode()
    for kpi in ("unidades_entregadas", "ventas_entregadas_hoy"):
        url = _href(html, kpi)
        assert "tipo_fecha=fecha_entrega" in url
        assert f"fecha_inicio={HOY}" in url and f"fecha_fin={HOY}" in url


def test_admin_con_negocio_elegido_lo_pasa_al_historial(logged_client):
    html = logged_client.get("/?negocio=2").data.decode()
    assert "id_negocio=2" in _href(html, "ventas_hoy")


def test_admin_todos_no_pasa_negocio(logged_client):
    assert "id_negocio" not in _href(logged_client.get("/").data.decode(), "ventas_hoy")


def test_caja_no_pasa_negocio_en_el_enlace(logged_client_caja):
    html = logged_client_caja.get("/").data.decode()
    assert "id_negocio" not in _href(html, "ventas_hoy")


def test_ingresos_hoy_no_es_enlace(logged_client):
    html = logged_client.get("/").data.decode()
    assert not re.search(r'<a[^>]*>(?:(?!</a>).)*data-kpi="ingresos_hoy"', html, re.S)


def test_historial_de_hoy_coincide_con_kpi_ventas(logged_client, venta_pendiente):
    kpis = logged_client.get("/api/index/kpis?negocio=all").get_json()
    total = contar_historial_ventas(fecha_inicio=HOY, fecha_fin=HOY, tipo_fecha="fecha_recibo")
    assert total == kpis["ventas_hoy"]
