"""
Servicios: búsqueda por nombre y servicio predeterminado por negocio
(negocio.id_servicio_default).
"""
import pytest

from models.servicios import obtener_servicios


@pytest.fixture
def sin_defaults(db_conn):
    """Guarda los predeterminados actuales, los limpia y los restaura al final."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT id_negocio, id_servicio_default FROM negocio")
    antes = cursor.fetchall()
    cursor.execute("UPDATE negocio SET id_servicio_default = NULL")
    db_conn.commit()
    yield
    for id_negocio, id_servicio in antes:
        cursor.execute("UPDATE negocio SET id_servicio_default = %s WHERE id_negocio = %s",
                       (id_servicio, id_negocio))
    db_conn.commit()
    cursor.close()


def _default_de(db_conn, id_negocio):
    db_conn.commit()  # cierra la transacción: con REPEATABLE READ se leería una foto vieja
    cursor = db_conn.cursor()
    cursor.execute("SELECT id_servicio_default FROM negocio WHERE id_negocio = %s", (id_negocio,))
    valor = cursor.fetchone()[0]
    cursor.close()
    return valor


def _limpiar_historial(db_conn, *ids):
    # Los fixtures de servicio borran el servicio pero no su historial
    cursor = db_conn.cursor()
    for sid in ids:
        cursor.execute("DELETE FROM servicios_historial WHERE id_servicio = %s", (sid,))
    db_conn.commit()
    cursor.close()


# ---------------------------------------------------------------------------
# Búsqueda por nombre
# ---------------------------------------------------------------------------

def test_pagina_servicios_tiene_buscador(logged_client):
    html = logged_client.get("/servicios").data.decode()
    assert 'id="buscar-servicio" name="q"' in html


def test_buscar_servicio_por_nombre(logged_client, servicio_calzado, servicio_confeccion):
    res = logged_client.get("/servicios?partial=1&q=Limpieza Test")
    assert b"Limpieza Test" in res.data
    assert b"Bordado Test" not in res.data


def test_buscar_servicio_por_parte_del_nombre(logged_client, servicio_confeccion):
    assert b"Bordado Test" in logged_client.get("/servicios?partial=1&q=borda").data


def test_buscar_conserva_texto_en_el_campo(logged_client):
    assert 'value="Bordado"' in logged_client.get("/servicios?q=Bordado").data.decode()


# ---------------------------------------------------------------------------
# Servicio predeterminado
# ---------------------------------------------------------------------------

def test_marcar_y_quitar_default(logged_client, db_conn, sin_defaults, servicio_calzado):
    sid = servicio_calzado["id_servicio"]

    data = logged_client.post(f"/servicios/{sid}/default").get_json()
    assert data["ok"] is True and data["es_default"] is True
    assert _default_de(db_conn, 1) == sid

    data = logged_client.post(f"/servicios/{sid}/default").get_json()
    assert data["es_default"] is False
    assert _default_de(db_conn, 1) is None
    _limpiar_historial(db_conn, sid)


def test_solo_un_default_por_negocio(logged_client, db_conn, sin_defaults, servicio_calzado):
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO servicio (id_negocio, nombre, precio, activo) VALUES (1, 'Otro Test', 80, 1)")
    otro = cursor.lastrowid
    db_conn.commit()
    try:
        logged_client.post(f"/servicios/{servicio_calzado['id_servicio']}/default")
        logged_client.post(f"/servicios/{otro}/default")
        assert _default_de(db_conn, 1) == otro
    finally:
        cursor.execute("UPDATE negocio SET id_servicio_default = NULL WHERE id_servicio_default = %s", (otro,))
        cursor.execute("DELETE FROM servicios_historial WHERE id_servicio IN (%s, %s)",
                       (otro, servicio_calzado["id_servicio"]))
        cursor.execute("DELETE FROM servicio WHERE id_servicio = %s", (otro,))
        db_conn.commit()
        cursor.close()


def test_default_no_afecta_a_otros_negocios(logged_client, db_conn, sin_defaults,
                                            servicio_calzado, servicio_confeccion):
    logged_client.post(f"/servicios/{servicio_calzado['id_servicio']}/default")
    logged_client.post(f"/servicios/{servicio_confeccion['id_servicio']}/default")
    assert _default_de(db_conn, 1) == servicio_calzado["id_servicio"]
    assert _default_de(db_conn, 2) == servicio_confeccion["id_servicio"]
    _limpiar_historial(db_conn, servicio_calzado["id_servicio"], servicio_confeccion["id_servicio"])


def test_api_servicios_indica_el_default(logged_client, db_conn, sin_defaults, servicio_calzado):
    sid = servicio_calzado["id_servicio"]
    logged_client.post(f"/servicios/{sid}/default")
    servicios = logged_client.get("/api/servicios?id_negocio=1").get_json()
    marcados = [s["id_servicio"] for s in servicios if s["es_default"]]
    assert marcados == [sid]
    _limpiar_historial(db_conn, sid)


def test_eliminar_servicio_quita_el_default(logged_client, db_conn, sin_defaults, servicio_calzado):
    sid = servicio_calzado["id_servicio"]
    logged_client.post(f"/servicios/{sid}/default")
    logged_client.post(f"/servicios/eliminar/{sid}")
    assert _default_de(db_conn, 1) is None
    _limpiar_historial(db_conn, sid)


def test_cambiar_de_negocio_quita_el_default(logged_client, db_conn, sin_defaults, servicio_calzado):
    sid = servicio_calzado["id_servicio"]
    logged_client.post(f"/servicios/{sid}/default")
    logged_client.post("/servicios/guardar", data={
        "id_servicio": sid, "id_negocio": "2", "nombre": "Limpieza Test", "precio": "150",
    })
    assert _default_de(db_conn, 1) is None
    _limpiar_historial(db_conn, sid)


def test_no_se_puede_marcar_servicio_eliminado(logged_client, db_conn, sin_defaults, servicio_calzado):
    sid = servicio_calzado["id_servicio"]
    logged_client.post(f"/servicios/eliminar/{sid}")
    assert logged_client.post(f"/servicios/{sid}/default").status_code == 404
    _limpiar_historial(db_conn, sid)


def test_caja_no_puede_marcar_default(logged_client_caja, servicio_calzado):
    assert logged_client_caja.post(f"/servicios/{servicio_calzado['id_servicio']}/default").status_code == 403


def test_tabla_muestra_estrella(logged_client, db_conn, sin_defaults, servicio_calzado):
    sid = servicio_calzado["id_servicio"]
    html = logged_client.get("/servicios?partial=1&q=Limpieza Test").data.decode()
    assert "js-default-servicio" in html and "is-default" not in html

    logged_client.post(f"/servicios/{sid}/default")
    html = logged_client.get("/servicios?partial=1&q=Limpieza Test").data.decode()
    assert "js-default-servicio is-default" in html
    assert 'aria-pressed="true"' in html
    _limpiar_historial(db_conn, sid)


def test_estrella_indica_el_default_anterior_para_confirmar(logged_client, db_conn, sin_defaults,
                                                           servicio_calzado):
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO servicio (id_negocio, nombre, precio, activo) VALUES (1, 'Otro Test', 80, 1)")
    otro = cursor.lastrowid
    db_conn.commit()
    try:
        logged_client.post(f"/servicios/{servicio_calzado['id_servicio']}/default")
        html = logged_client.get("/servicios?partial=1&q=Otro Test").data.decode()
        # La fila de "Otro Test" sabe cuál es el predeterminado actual de su negocio
        assert 'data-default-actual="Limpieza Test"' in html

        html = logged_client.get("/servicios?partial=1&q=Limpieza Test").data.decode()
        # El que ya es predeterminado no pide confirmación (solo se quita)
        assert 'data-default-actual=""' in html
    finally:
        cursor.execute("DELETE FROM servicios_historial WHERE id_servicio IN (%s, %s)",
                       (otro, servicio_calzado["id_servicio"]))
        cursor.execute("DELETE FROM servicio WHERE id_servicio = %s", (otro,))
        db_conn.commit()
        cursor.close()


def test_pagina_tiene_modal_de_confirmacion(logged_client):
    html = logged_client.get("/servicios").data.decode()
    assert 'id="modalConfirmarDefaultServicio"' in html
    assert "js-confirmar-default-servicio" in html


def test_filtro_de_negocio_es_compacto(logged_client):
    assert "filtro-item--negocio" in logged_client.get("/servicios").data.decode()


def test_obtener_servicios_es_default_sin_marcar(sin_defaults, servicio_calzado):
    filas = obtener_servicios(id_negocio=1, q="Limpieza Test", limit=10)
    assert filas and all(not f["es_default"] for f in filas)
