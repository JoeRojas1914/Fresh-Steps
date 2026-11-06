"""Formatos únicos de montos y fechas para las tablas (filtros de Jinja)."""
from datetime import date, datetime
from decimal import Decimal

from utils import dinero, fecha, fecha_hora

HOY = date(2026, 11, 5)


def test_dinero_dos_decimales_y_miles():
    assert dinero(70) == "$70.00"
    assert dinero(70.5) == "$70.50"
    assert dinero(Decimal("1234.5")) == "$1,234.50"
    assert dinero(None) == "$0.00"
    assert dinero(-25) == "-$25.00"


def test_fecha():
    assert fecha(date(2026, 11, 5)) == "5 nov 2026"
    assert fecha(datetime(2020, 1, 1, 9, 30)) == "1 ene 2020"
    assert fecha(None) == "—"


def test_fecha_hora_mismo_anio_sin_anio():
    assert fecha_hora(datetime(2026, 11, 5, 9, 5), hoy=HOY) == "5 nov 09:05"


def test_fecha_hora_otro_anio_con_anio():
    assert fecha_hora(datetime(2025, 12, 31, 21, 0), hoy=HOY) == "31 dic 2025 21:00"


def test_fecha_hora_sin_valor():
    assert fecha_hora(None) == "—"


def test_filtros_registrados_en_jinja(app):
    for nombre in ("dinero", "fecha", "fecha_hora"):
        assert nombre in app.jinja_env.filters


# ── Restaurar en Gastos y Servicios ───────────────────────────────────────────
# Antes era un <a href> (GET) y la ruta solo acepta POST → 405.

def test_partial_gastos_restaurar_es_boton_js(logged_client, db_conn, gasto_test):
    cur = db_conn.cursor()
    cur.execute("UPDATE gastos SET activo = 0 WHERE id_gasto = %s", (gasto_test["id_gasto"],))
    db_conn.commit()
    cur.close()
    html = logged_client.get("/gastos?partial=1&eliminados=1").data.decode()
    assert f'href="/gastos/restaurar/{gasto_test["id_gasto"]}"' not in html
    assert "js-restaurar-gasto" in html


def test_partial_servicios_restaurar_no_es_enlace(logged_client):
    html = logged_client.get("/servicios?partial=1&eliminados=1").data.decode()
    assert 'href="/servicios/restaurar/' not in html


def test_restaurar_gasto_por_post(logged_client, db_conn, gasto_test):
    cur = db_conn.cursor()
    cur.execute("UPDATE gastos SET activo = 0 WHERE id_gasto = %s", (gasto_test["id_gasto"],))
    db_conn.commit()
    cur.close()
    resp = logged_client.post(f"/gastos/restaurar/{gasto_test['id_gasto']}")
    assert resp.status_code == 200 and resp.get_json()["ok"] is True
