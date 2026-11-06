"""Prepago al registrar una venta (hallazgo C3 de reviews/audit-plan-full.md).

La venta, sus artículos y el prepago se guardan en una sola transacción:
si el prepago no es válido no debe quedar ninguna venta guardada.
"""
import pytest

from services.ventas_service import guardar_venta_service
from tests.conftest import cleanup_venta


def _form(cliente_test, servicio_calzado, **extra):
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
        "articulos[0][servicios][0][precio_aplicado]": "150.00",
    }
    form.update(extra)
    return form


def _ventas(db_conn, id_cliente):
    db_conn.commit()
    cur = db_conn.cursor(dictionary=True)
    cur.execute("SELECT id_venta FROM venta WHERE id_cliente = %s", (id_cliente,))
    ids = [r["id_venta"] for r in cur.fetchall()]
    cur.close()
    return ids


def _guardar(app, form, usuario_admin):
    with app.test_request_context("/"):
        return guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])


@pytest.mark.parametrize("extra,mensaje", [
    ({"prepago": "si", "monto_prepago": "50", "tipo_pago": "cripto"}, "Método de pago no válido"),
    ({"prepago": "si", "monto_prepago": "-10", "tipo_pago": "efectivo"}, "monto del prepago no es válido"),
    ({"prepago": "si", "monto_prepago": "abc", "tipo_pago": "efectivo"}, "monto del prepago no es válido"),
    ({"prepago": "si", "monto_prepago": "150.01", "tipo_pago": "efectivo"}, "mayor al total"),
])
def test_prepago_invalido_no_guarda_la_venta(app, db_conn, usuario_admin, cliente_test, servicio_calzado,
                                             extra, mensaje):
    id_venta, error = _guardar(app, _form(cliente_test, servicio_calzado, **extra), usuario_admin)
    try:
        assert id_venta is None
        assert mensaje in error
        assert _ventas(db_conn, cliente_test["id_cliente"]) == []
    finally:
        for idv in _ventas(db_conn, cliente_test["id_cliente"]):
            cleanup_venta(db_conn, idv)


def test_prepago_valido_se_guarda_como_prepago(app, db_conn, usuario_admin, cliente_test, servicio_calzado):
    form = _form(cliente_test, servicio_calzado, prepago="si", monto_prepago="150.00", tipo_pago="tarjeta")
    id_venta, error = _guardar(app, form, usuario_admin)
    try:
        assert error is None and id_venta
        cur = db_conn.cursor(dictionary=True)
        db_conn.commit()
        cur.execute("SELECT monto, tipo_pago, tipo_pago_venta FROM pago_venta WHERE id_venta = %s", (id_venta,))
        pagos = cur.fetchall()
        cur.close()
        assert len(pagos) == 1
        assert float(pagos[0]["monto"]) == 150.0
        assert pagos[0]["tipo_pago"] == "tarjeta"
        assert pagos[0]["tipo_pago_venta"] == "prepago"
    finally:
        if id_venta:
            cleanup_venta(db_conn, id_venta)


def test_sin_prepago_no_registra_pago(app, db_conn, usuario_admin, cliente_test, servicio_calzado):
    id_venta, error = _guardar(app, _form(cliente_test, servicio_calzado, prepago="no"), usuario_admin)
    try:
        assert error is None
        cur = db_conn.cursor(dictionary=True)
        db_conn.commit()
        cur.execute("SELECT COUNT(*) AS n FROM pago_venta WHERE id_venta = %s", (id_venta,))
        assert cur.fetchone()["n"] == 0
        cur.close()
    finally:
        cleanup_venta(db_conn, id_venta)
