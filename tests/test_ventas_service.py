"""
Tests para services/ventas_service.py — reglas de negocio de creación de ventas.
Los casos 1-7 validan lógica pura (sin tocar BD).
Los casos 8-10 hacen INSERT real y limpian al terminar.
"""
import pytest
from services.ventas_service import guardar_venta_service, registrar_pago_final_service
from tests.conftest import cleanup_venta


FECHA = "2030-12-31 10:00:00"


# ---------------------------------------------------------------------------
# Helpers para construir forms de prueba
# ---------------------------------------------------------------------------

def _form_maquila(id_cliente=None, fecha=FECHA, con_servicios=False):
    form = {
        "id_negocio": "3",
        "articulos[0][tipo_articulo]": "maquila",
        "articulos[0][tipo]": "Mandil",
        "articulos[0][cantidad]": "5",
        "articulos[0][precio_unitario]": "50.00",
    }
    if id_cliente:
        form["id_cliente"] = str(id_cliente)
    if fecha:
        form["fecha_estimada"] = fecha
    if con_servicios:  # pragma: no cover
        form["articulos[0][servicios][0][id_servicio]"] = "1"
        form["articulos[0][servicios][0][precio_aplicado]"] = "100"
    return form


def _form_calzado(id_cliente, id_servicio, precio_servicio="150.00", fecha=FECHA):
    return {
        "id_negocio": "1",
        "id_cliente": str(id_cliente),
        "fecha_estimada": fecha,
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Tenis",
        "articulos[0][marca]": "Nike",
        "articulos[0][material]": "Piel",
        "articulos[0][color_base]": "Blanco",
        f"articulos[0][servicios][0][id_servicio]": str(id_servicio),
        f"articulos[0][servicios][0][precio_aplicado]": precio_servicio,
    }


# ---------------------------------------------------------------------------
# Casos 1-7: validaciones (sin BD)
# ---------------------------------------------------------------------------

def test_sin_cliente_retorna_error(app):
    form = _form_maquila(id_cliente=None)
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=1)
    assert id_venta is None
    assert "obligatorio" in error.lower()


def test_sin_fecha_estimada_retorna_error(app):
    form = _form_maquila(id_cliente=99999, fecha=None)
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=1)
    assert id_venta is None
    assert "obligatorio" in error.lower()


def test_sin_articulos_retorna_error(app):
    form = {
        "id_negocio": "3",
        "id_cliente": "99999",
        "fecha_estimada": FECHA,
    }
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=1)
    assert id_venta is None
    assert "artículo" in error.lower()


def test_tipo_articulo_incorrecto_para_negocio(app):
    """Negocio 1 (calzado) rechaza artículo de tipo confección."""
    form = {
        "id_negocio": "1",
        "id_cliente": "99999",
        "fecha_estimada": FECHA,
        "articulos[0][tipo_articulo]": "confeccion",
        "articulos[0][tipo]": "Pantalón",
        "articulos[0][marca]": "Levis",
        "articulos[0][material]": "Mezclilla",
        "articulos[0][color_base]": "Azul",
        "articulos[0][cantidad]": "1",
    }
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=1)
    assert id_venta is None
    assert "calzado" in error.lower()


def test_calzado_sin_servicios_retorna_error(app):
    form = {
        "id_negocio": "1",
        "id_cliente": "99999",
        "fecha_estimada": FECHA,
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Tenis",
        "articulos[0][marca]": "Nike",
        "articulos[0][material]": "Piel",
        "articulos[0][color_base]": "Blanco",
    }
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=1)
    assert id_venta is None
    assert "servicio" in error.lower()


def test_calzado_precio_servicio_cero_retorna_error(app):
    form = {
        "id_negocio": "1",
        "id_cliente": "99999",
        "fecha_estimada": FECHA,
        "articulos[0][tipo_articulo]": "calzado",
        "articulos[0][tipo]": "Tenis",
        "articulos[0][marca]": "Nike",
        "articulos[0][material]": "Piel",
        "articulos[0][color_base]": "Blanco",
        "articulos[0][servicios][0][id_servicio]": "1",
        "articulos[0][servicios][0][precio_aplicado]": "0",
    }
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=1)
    assert id_venta is None
    assert "precio" in error.lower()


def test_negocio_id_invalido_retorna_error(app):
    form = {"id_negocio": "no_es_numero"}
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=1)
    assert id_venta is None
    assert "negocio" in error.lower()


# ---------------------------------------------------------------------------
# Casos 8-10: integración con BD real
# ---------------------------------------------------------------------------

def test_venta_calzado_valida_crea_registro(app, db_conn, cliente_test, servicio_calzado, usuario_admin):
    form = _form_calzado(
        id_cliente=cliente_test["id_cliente"],
        id_servicio=servicio_calzado["id_servicio"],
    )
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])
    try:
        assert error is None
        assert isinstance(id_venta, int) and id_venta > 0
    finally:
        if id_venta:
            cleanup_venta(db_conn, id_venta)


def test_venta_maquila_valida_crea_registro(app, db_conn, cliente_test, usuario_admin):
    form = _form_maquila(
        id_cliente=cliente_test["id_cliente"],
    )
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])
    try:
        assert error is None
        assert isinstance(id_venta, int) and id_venta > 0
    finally:
        if id_venta:
            cleanup_venta(db_conn, id_venta)


def test_pago_final_sin_datos_retorna_error(app):
    with app.test_request_context("/"):
        ok, mensaje = registrar_pago_final_service({}, id_usuario=1)
    assert ok is False
    assert "incompleto" in mensaje.lower()


def test_venta_confeccion_valida_crea_registro(app, db_conn, cliente_test, servicio_confeccion, usuario_admin):
    form = {
        "id_negocio": "2",
        "id_cliente": str(cliente_test["id_cliente"]),
        "fecha_estimada": FECHA,
        "articulos[0][tipo_articulo]": "confeccion",
        "articulos[0][tipo]": "Camisa",
        "articulos[0][marca]": "Levis",
        "articulos[0][material]": "Algodón",
        "articulos[0][color_base]": "Blanco",
        "articulos[0][cantidad]": "3",
        f"articulos[0][servicios][0][id_servicio]": str(servicio_confeccion["id_servicio"]),
        f"articulos[0][servicios][0][precio_aplicado]": "200.00",
    }
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])
    try:
        assert error is None
        assert isinstance(id_venta, int) and id_venta > 0
    finally:
        if id_venta:
            cleanup_venta(db_conn, id_venta)


def test_pago_final_valido_registra_y_marca_entregada(app, db_conn, cliente_test, servicio_calzado, usuario_admin):
    form = _form_calzado(
        id_cliente=cliente_test["id_cliente"],
        id_servicio=servicio_calzado["id_servicio"],
    )
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])
    assert error is None

    try:
        ok, _ = registrar_pago_final_service(
            {"id_venta": id_venta, "monto": "150.00", "metodo_pago": "efectivo"},
            id_usuario=usuario_admin["id_usuario"],
        )
        assert ok is True

        cursor = db_conn.cursor(dictionary=True)
        cursor.execute("SELECT fecha_entrega FROM venta WHERE id_venta = %s", (id_venta,))
        row = cursor.fetchone()
        cursor.close()
        assert row["fecha_entrega"] is not None
    finally:
        cleanup_venta(db_conn, id_venta)


def test_venta_maquila_multiples_articulos(app, db_conn, cliente_test, usuario_admin):
    form = {
        "id_negocio": "3",
        "id_cliente": str(cliente_test["id_cliente"]),
        "fecha_estimada": FECHA,
        "articulos[0][tipo_articulo]": "maquila",
        "articulos[0][tipo]": "Mandil",
        "articulos[0][cantidad]": "5",
        "articulos[0][precio_unitario]": "50.00",
        "articulos[1][tipo_articulo]": "maquila",
        "articulos[1][tipo]": "Delantal",
        "articulos[1][cantidad]": "3",
        "articulos[1][precio_unitario]": "80.00",
    }
    with app.test_request_context("/"):
        id_venta, error = guardar_venta_service(form, id_usuario_creo=usuario_admin["id_usuario"])
    try:
        assert error is None
        assert isinstance(id_venta, int) and id_venta > 0
    finally:
        if id_venta:
            cleanup_venta(db_conn, id_venta)
