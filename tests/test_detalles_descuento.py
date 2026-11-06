"""Los detalles de la venta avisan cuando la venta tiene descuento."""


def _aplicar_descuento(db_conn, id_venta, monto):
    cur = db_conn.cursor()
    cur.execute(
        "UPDATE venta SET aplica_descuento = 1, cantidad_descuento = %s WHERE id_venta = %s",
        (monto, id_venta),
    )
    db_conn.commit()
    cur.close()


def _fila(html, id_venta):
    inicio = html.index(f'id="detalles-{id_venta}"')
    return html[inicio:html.index("</tr>", inicio)]


def test_pendientes_avisa_descuento(logged_client, db_conn, venta_pendiente):
    id_venta = venta_pendiente["id_venta"]
    _aplicar_descuento(db_conn, id_venta, 20)
    html = logged_client.get(f"/ventas/pendientes?partial=1&id_venta={id_venta}").data.decode()
    fila = _fila(html, id_venta)
    assert "Con descuento de $20.00" in fila
    assert 'data-descuento="20.00"' in fila


def test_historial_avisa_descuento(logged_client, db_conn, venta_pendiente):
    id_venta = venta_pendiente["id_venta"]
    _aplicar_descuento(db_conn, id_venta, 15.5)
    html = logged_client.get(f"/ventas/historial?partial=1&id_venta={id_venta}").data.decode()
    assert "Con descuento de $15.50" in _fila(html, id_venta)


def test_sin_descuento_no_avisa(logged_client, venta_pendiente):
    id_venta = venta_pendiente["id_venta"]
    html = logged_client.get(f"/ventas/pendientes?partial=1&id_venta={id_venta}").data.decode()
    fila = _fila(html, id_venta)
    assert "Con descuento" not in fila
    assert 'data-descuento="0.00"' in fila or 'data-descuento="0"' in fila
