"""
Badge de semanas en Procesadas: cuánto tiempo lleva una venta lista sin recogerse.
"""
from datetime import date, datetime, timedelta

from services.ventas_service import semanas_desde

HOY = date(2026, 11, 1)


def test_semanas_desde_menos_de_una_semana_es_cero():
    assert semanas_desde(HOY, HOY) == 0
    assert semanas_desde(HOY - timedelta(days=6), HOY) == 0


def test_semanas_desde_cuenta_semanas_completas():
    assert semanas_desde(HOY - timedelta(days=7), HOY) == 1
    assert semanas_desde(HOY - timedelta(days=13), HOY) == 1
    assert semanas_desde(HOY - timedelta(days=14), HOY) == 2
    assert semanas_desde(HOY - timedelta(days=30), HOY) == 4


def test_semanas_desde_acepta_datetime_y_vacios():
    assert semanas_desde(datetime(2026, 10, 18, 23, 59), HOY) == 2
    assert semanas_desde(None, HOY) == 0
    assert semanas_desde(HOY + timedelta(days=10), HOY) == 0


def _marcar_lista_hace(db_conn, id_venta, dias):
    cursor = db_conn.cursor()
    cursor.execute(
        "UPDATE venta SET fecha_lista = %s WHERE id_venta = %s",
        (datetime.now() - timedelta(days=dias), id_venta),
    )
    db_conn.commit()
    cursor.close()


def _fila(html, id_venta):
    """HTML de la fila principal de esa venta (hasta su fila de detalles)."""
    inicio = html.index(f"<td>#{id_venta}</td>")
    return html[inicio:html.index(f'id="detalles-{id_venta}"', inicio)]


def test_procesadas_muestra_badge_despues_de_una_semana(logged_client, db_conn, venta_pendiente):
    id_venta = venta_pendiente["id_venta"]
    _marcar_lista_hace(db_conn, id_venta, 15)
    html = logged_client.get(f"/ventas/listas?partial=1&id_venta={id_venta}").data.decode()
    fila = _fila(html, id_venta)
    assert "badge-semanas" in fila
    assert "2 semanas" in fila


def test_procesadas_sin_badge_antes_de_una_semana(logged_client, db_conn, venta_pendiente):
    id_venta = venta_pendiente["id_venta"]
    _marcar_lista_hace(db_conn, id_venta, 3)
    html = logged_client.get(f"/ventas/listas?partial=1&id_venta={id_venta}").data.decode()
    assert "badge-semanas" not in _fila(html, id_venta)


def test_procesadas_badge_rojo_desde_cuatro_semanas(logged_client, db_conn, venta_pendiente):
    id_venta = venta_pendiente["id_venta"]
    _marcar_lista_hace(db_conn, id_venta, 30)
    html = logged_client.get(f"/ventas/listas?partial=1&id_venta={id_venta}").data.decode()
    assert "badge-semanas--alta" in _fila(html, id_venta)


def test_procesadas_ordena_por_fecha_lista(logged_client):
    res = logged_client.get("/ventas/listas?partial=1&orden=fecha_lista&dir=asc")
    assert res.status_code == 200
    assert b"Fecha lista" in res.data


def test_procesadas_ya_no_muestra_fecha_estimada(logged_client):
    res = logged_client.get("/ventas/listas?partial=1")
    assert b"Fecha estimada" not in res.data
