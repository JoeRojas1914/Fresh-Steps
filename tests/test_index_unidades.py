"""
Línea de "unidades recibidas" en la gráfica semanal del inicio.
"""
from datetime import date, timedelta

from models.estadisticas_ventas import contar_unidades_hoy, contar_unidades_por_dia_rango


def _semana():
    hoy   = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    return lunes, lunes + timedelta(days=5)


def test_unidades_por_dia_rellena_dias_vacios():
    lunes, sabado = _semana()
    serie = contar_unidades_por_dia_rango(lunes, sabado)
    assert len(serie) == 6
    assert all(isinstance(d["total"], int) and d["total"] >= 0 for d in serie)


def test_unidades_de_hoy_coinciden_con_kpi(venta_pendiente):
    hoy = date.today()
    assert contar_unidades_por_dia_rango(hoy, hoy)[0]["total"] == contar_unidades_hoy("fecha_recibo")


def test_unidades_por_dia_respeta_negocio(venta_pendiente):
    # venta_pendiente es de Calzado (1): sus artículos no cuentan en Confección (2)
    hoy = date.today()
    todos   = contar_unidades_por_dia_rango(hoy, hoy)[0]["total"]
    calzado = contar_unidades_por_dia_rango(hoy, hoy, [1])[0]["total"]
    otros   = contar_unidades_por_dia_rango(hoy, hoy, [2, 3])[0]["total"]
    assert calzado >= 1
    assert calzado + otros == todos


def test_api_kpis_incluye_unidades_de_la_semana(logged_client):
    data = logged_client.get("/api/index/kpis?negocio=all").get_json()
    assert len(data["chart_unidades"]) == len(data["chart_labels"]) == 6


def test_index_pasa_unidades_a_la_grafica(logged_client):
    html = logged_client.get("/").data.decode()
    assert '"unidades":' in html
    assert "Unidades recibidas" in html
