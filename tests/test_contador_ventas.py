"""
Contador de ventas y artículos arriba de /ventas/pendientes y /ventas/listas.

El contador se calcula con los mismos filtros que la tabla, así que debe
coincidir con los conteos del modelo para esos filtros.
"""
from models.ventas import (
    contar_articulos_entregas,
    contar_entregas_listas,
    contar_entregas_pendientes,
    marcar_como_lista,
)


def _contador(html: bytes, clave: str, valor: int) -> bool:
    return f'data-contador="{clave}">{valor}<'.encode() in html


def test_contar_articulos_venta_pendiente(venta_pendiente):
    assert contar_articulos_entregas(False, id_venta=venta_pendiente["id_venta"]) >= 1


def test_contar_articulos_respeta_filtro_de_negocio(venta_pendiente):
    # venta_pendiente es de Calzado (1): filtrando por Confección no cuenta sus artículos
    id_venta = venta_pendiente["id_venta"]
    con_calzado = contar_articulos_entregas(False, id_negocio=1, id_venta=id_venta)
    sin_calzado = contar_articulos_entregas(False, id_negocio=2, id_venta=id_venta)
    assert con_calzado >= 1
    assert sin_calzado < con_calzado


def test_contador_pendientes_coincide_con_filtros(logged_client, venta_pendiente):
    id_venta = venta_pendiente["id_venta"]
    ventas    = contar_entregas_pendientes(None, str(id_venta))
    articulos = contar_articulos_entregas(False, id_venta=str(id_venta))

    res = logged_client.get(f"/ventas/pendientes?partial=1&id_venta={id_venta}")
    assert res.status_code == 200
    assert _contador(res.data, "ventas", ventas)
    assert _contador(res.data, "articulos", articulos)
    assert b"con los filtros aplicados" in res.data


def test_contador_listas_coincide_con_filtros(logged_client, venta_pendiente, usuario_admin):
    id_venta = venta_pendiente["id_venta"]
    marcar_como_lista(id_venta, usuario_admin["id_usuario"])

    ventas    = contar_entregas_listas(None, str(id_venta))
    articulos = contar_articulos_entregas(True, id_venta=str(id_venta))
    assert ventas >= 1 and articulos >= 1

    res = logged_client.get(f"/ventas/listas?partial=1&id_venta={id_venta}")
    assert res.status_code == 200
    assert _contador(res.data, "ventas", ventas)
    assert _contador(res.data, "articulos", articulos)


def test_contador_aparece_en_pagina_completa(logged_client):
    for url in ("/ventas/pendientes", "/ventas/listas"):
        res = logged_client.get(url)
        assert res.status_code == 200
        assert b'class="contador-ventas"' in res.data
        assert b'data-contador="articulos"' in res.data
        assert b"con los filtros aplicados" not in res.data


def test_contador_caja_solo_cuenta_sus_negocios(
    logged_client_caja, usuario_caja, db_conn, venta_pendiente
):
    # Caja limitada a Confección: la venta de Calzado no entra en el contador
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM usuario_negocio WHERE id_usuario = %s", (usuario_caja["id_usuario"],))
    cursor.execute(
        "INSERT INTO usuario_negocio (id_usuario, id_negocio) VALUES (%s, 2)",
        (usuario_caja["id_usuario"],),
    )
    db_conn.commit()
    cursor.close()

    esperado = contar_articulos_entregas(False, id_negocio=[2])
    res = logged_client_caja.get("/ventas/pendientes?partial=1")
    assert _contador(res.data, "articulos", esperado)
