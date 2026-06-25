"""
Tests para services/ventas_editar_service.py.
Cubre parsers puros, validaciones y el flujo completo de edición.
"""
import pytest
from decimal import Decimal

from services.ventas_editar_service import (
    _parsear_servicios_nuevos,
    _parsear_ediciones_servicio,
    _parsear_ediciones_articulo,
    _parsear_eliminaciones_servicio,
    _validar_precios_edicion,
    obtener_venta_editar_service,
    editar_venta_service,
)


# ===========================================================================
# Parsers de formulario (tests unitarios puros)
# ===========================================================================

def test_parsear_servicios_nuevos_vacio():
    assert _parsear_servicios_nuevos({}) == []


def test_parsear_servicios_nuevos_un_servicio():
    form = {
        "existing_servicios[10][0][id_servicio]": "5",
        "existing_servicios[10][0][precio_aplicado]": "120.00",
    }
    result = _parsear_servicios_nuevos(form)
    assert len(result) == 1
    assert result[0]["id_articulo"] == 10
    assert len(result[0]["servicios"]) == 1
    assert result[0]["servicios"][0]["id_servicio"] == 5
    assert result[0]["servicios"][0]["precio_aplicado"] == Decimal("120.00")


def test_parsear_servicios_nuevos_sin_id_servicio_ignora():
    form = {
        "existing_servicios[10][0][precio_aplicado]": "100.00",
    }
    result = _parsear_servicios_nuevos(form)
    assert result == []


def test_parsear_servicios_nuevos_multiples_articulos():
    form = {
        "existing_servicios[1][0][id_servicio]": "3",
        "existing_servicios[1][0][precio_aplicado]": "50.00",
        "existing_servicios[2][0][id_servicio]": "4",
        "existing_servicios[2][0][precio_aplicado]": "80.00",
    }
    result = _parsear_servicios_nuevos(form)
    assert len(result) == 2
    ids_art = {e["id_articulo"] for e in result}
    assert ids_art == {1, 2}


def test_parsear_ediciones_servicio_vacio():
    assert _parsear_ediciones_servicio({}) == []


def test_parsear_ediciones_servicio_una_edicion():
    form = {
        "existing_edit[10][5][precio_aplicado]": "200.00",
    }
    result = _parsear_ediciones_servicio(form)
    assert len(result) == 1
    assert result[0]["id_articulo"] == 10
    assert result[0]["id_servicio"] == 5
    assert result[0]["precio_aplicado"] == Decimal("200.00")


def test_parsear_ediciones_articulo_vacio():
    assert _parsear_ediciones_articulo({}) == {}


def test_parsear_ediciones_articulo_un_campo():
    form = {
        "art_edit[7][marca]": "Adidas",
        "art_edit[7][color_base]": "Rojo",
    }
    result = _parsear_ediciones_articulo(form)
    assert result[7]["marca"] == "Adidas"
    assert result[7]["color_base"] == "Rojo"


def test_parsear_eliminaciones_servicio_vacio():
    assert _parsear_eliminaciones_servicio({}) == []


def test_parsear_eliminaciones_servicio_una():
    form = {
        "existing_delete[10][5]": "1",
    }
    result = _parsear_eliminaciones_servicio(form)
    assert len(result) == 1
    assert result[0]["id_articulo"] == 10
    assert result[0]["id_servicio"] == 5


def test_parsear_eliminaciones_servicio_valor_cero_ignora():
    form = {
        "existing_delete[10][5]": "0",
    }
    result = _parsear_eliminaciones_servicio(form)
    assert result == []


# ===========================================================================
# Validar precios de edición
# ===========================================================================

def test_validar_precios_edicion_vacio_ok():
    _validar_precios_edicion([])


def test_validar_precios_edicion_positivo_ok():
    _validar_precios_edicion([{"precio_aplicado": Decimal("50.00")}])


def test_validar_precios_edicion_cero_lanza():
    with pytest.raises(ValueError, match="mayor a"):
        _validar_precios_edicion([{"precio_aplicado": Decimal("0")}])


def test_validar_precios_edicion_negativo_lanza():
    with pytest.raises(ValueError, match="mayor a"):
        _validar_precios_edicion([{"precio_aplicado": Decimal("-10")}])


# ===========================================================================
# obtener_venta_editar_service
# ===========================================================================

def test_obtener_venta_editar_inexistente_lanza():
    with pytest.raises(ValueError, match="no encontrada"):
        obtener_venta_editar_service(999999)


def test_obtener_venta_editar_pendiente_retorna_datos(venta_pendiente):
    data = obtener_venta_editar_service(venta_pendiente["id_venta"])
    assert "venta" in data
    assert "articulos_existentes" in data
    assert isinstance(data["articulos_existentes"], list)
    assert len(data["articulos_existentes"]) > 0


# ===========================================================================
# editar_venta_service
# ===========================================================================

def test_editar_venta_service_inexistente_lanza():
    with pytest.raises(ValueError, match="no encontrada"):
        editar_venta_service(999999, {}, id_usuario=1)


def test_editar_venta_service_sin_cambios_lanza(venta_pendiente, usuario_admin):
    with pytest.raises(ValueError, match="No hay cambios"):
        editar_venta_service(
            venta_pendiente["id_venta"],
            {},
            id_usuario=usuario_admin["id_usuario"],
        )


def test_editar_venta_service_cambia_fecha(venta_pendiente, usuario_admin):
    result = editar_venta_service(
        venta_pendiente["id_venta"],
        {
            "fecha_estimada_fecha": "2031-03-20",
            "fecha_estimada_hora": "09:00",
        },
        id_usuario=usuario_admin["id_usuario"],
    )
    assert "total_nuevo" in result
    assert result["total_nuevo"] >= 0


def test_editar_venta_service_edita_articulo(venta_pendiente, usuario_admin):
    id_art = venta_pendiente["id_articulo"]
    id_srv = venta_pendiente["id_servicio"]
    result = editar_venta_service(
        venta_pendiente["id_venta"],
        {
            f"existing_edit[{id_art}][{id_srv}][precio_aplicado]": "180.00",
        },
        id_usuario=usuario_admin["id_usuario"],
    )
    assert "total_nuevo" in result
    assert float(result["total_nuevo"]) == 180.00


# ===========================================================================
# models/ventas_editar.py — cobertura directa de la capa de modelo
# ===========================================================================

def test_obtener_articulos_con_servicios_venta_inexistente():
    """Line 82: retorna [] cuando la venta no existe."""
    from models.ventas_editar import obtener_articulos_con_servicios
    result = obtener_articulos_con_servicios(999999)
    assert result == []


def test_editar_venta_modelo_venta_inexistente_raises():
    """Line 127: ValueError cuando la venta no está pendiente."""
    from models.ventas_editar import editar_venta
    with pytest.raises(ValueError, match="no existe"):
        editar_venta(
            id_venta=999999,
            fecha_estimada=None,
            nuevos_articulos=[],
            nuevos_servicios_por_articulo=[],
            ediciones_servicio=[],
            eliminaciones_servicio=[],
            id_usuario=1,
        )


def test_editar_venta_elimina_servicio_modelo_directo(venta_pendiente, usuario_admin):
    """Lines 165-179: eliminaciones_servicio procesa y borra el servicio."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    id_srv = venta_pendiente["id_servicio"]
    result = editar_venta(
        id_venta=venta_pendiente["id_venta"],
        fecha_estimada=None,
        nuevos_articulos=[],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[],
        eliminaciones_servicio=[{"id_articulo": id_art, "id_servicio": id_srv}],
        id_usuario=usuario_admin["id_usuario"],
    )
    assert "total_nuevo" in result
    assert float(result["total_nuevo"]) == 0.0


def test_editar_venta_skip_edicion_si_ya_eliminado(venta_pendiente, usuario_admin):
    """Line 188: edición del mismo servicio que fue eliminado es ignorada."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    id_srv = venta_pendiente["id_servicio"]
    result = editar_venta(
        id_venta=venta_pendiente["id_venta"],
        fecha_estimada=None,
        nuevos_articulos=[],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[{"id_articulo": id_art, "id_servicio": id_srv, "precio_aplicado": Decimal("200.00")}],
        eliminaciones_servicio=[{"id_articulo": id_art, "id_servicio": id_srv}],
        id_usuario=usuario_admin["id_usuario"],
    )
    assert float(result["total_nuevo"]) == 0.0


def test_editar_venta_mismo_precio_skip(venta_pendiente, usuario_admin):
    """Line 195: edición con precio idéntico al actual es ignorada."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    id_srv = venta_pendiente["id_servicio"]
    result = editar_venta(
        id_venta=venta_pendiente["id_venta"],
        fecha_estimada=None,
        nuevos_articulos=[],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[{"id_articulo": id_art, "id_servicio": id_srv, "precio_aplicado": Decimal("150.00")}],
        eliminaciones_servicio=[],
        id_usuario=usuario_admin["id_usuario"],
    )
    assert float(result["total_nuevo"]) == 150.0


def test_editar_venta_edita_campo_articulo_calzado(venta_pendiente, usuario_admin):
    """Lines 213-309: edición de campo de artículo calzado (campo no numérico → line 32)."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    result = editar_venta(
        id_venta=venta_pendiente["id_venta"],
        fecha_estimada=None,
        nuevos_articulos=[],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[],
        eliminaciones_servicio=[],
        id_usuario=usuario_admin["id_usuario"],
        ediciones_articulo={id_art: {"marca": "MarcaEditada"}},
    )
    assert "total_nuevo" in result


def test_editar_venta_campo_no_valido_para_tipo_skip(venta_pendiente, usuario_admin):
    """Lines 233-234: campo no pertenece al tipo → updates vacío → continue."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    result = editar_venta(
        id_venta=venta_pendiente["id_venta"],
        fecha_estimada="2031-06-01 10:00:00",
        nuevos_articulos=[],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[],
        eliminaciones_servicio=[],
        id_usuario=usuario_admin["id_usuario"],
        ediciones_articulo={id_art: {"precio_unitario": "99.00"}},
    )
    assert "total_nuevo" in result


def test_editar_venta_articulo_inexistente_skip(venta_pendiente, usuario_admin):
    """Lines 225-226: artículo no existe en la venta → continue."""
    from models.ventas_editar import editar_venta
    result = editar_venta(
        id_venta=venta_pendiente["id_venta"],
        fecha_estimada="2031-06-01 10:00:00",
        nuevos_articulos=[],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[],
        eliminaciones_servicio=[],
        id_usuario=usuario_admin["id_usuario"],
        ediciones_articulo={999999: {"marca": "Nada"}},
    )
    assert "total_nuevo" in result


def test_editar_venta_campo_requerido_vacio_raises(venta_pendiente, usuario_admin):
    """Lines 247-256: campo obligatorio vacío lanza ValueError."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    with pytest.raises(ValueError, match="obligatorio"):
        editar_venta(
            id_venta=venta_pendiente["id_venta"],
            fecha_estimada=None,
            nuevos_articulos=[],
            nuevos_servicios_por_articulo=[],
            ediciones_servicio=[],
            eliminaciones_servicio=[],
            id_usuario=usuario_admin["id_usuario"],
            ediciones_articulo={id_art: {"marca": ""}},
        )


def test_editar_venta_confeccion_cambia_cantidad(venta_confeccion, usuario_admin):
    """Lines 274-283: actualización de cantidad en confección ajusta el total."""
    from models.ventas_editar import editar_venta
    id_art = venta_confeccion["id_articulo"]
    result = editar_venta(
        id_venta=venta_confeccion["id_venta"],
        fecha_estimada=None,
        nuevos_articulos=[],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[],
        eliminaciones_servicio=[],
        id_usuario=usuario_admin["id_usuario"],
        ediciones_articulo={id_art: {"cantidad": "3"}},
    )
    assert float(result["total_nuevo"]) == 600.0


def test_editar_venta_maquila_cambia_precio_unitario(venta_maquila, usuario_admin):
    """Lines 284-289: actualización de precio_unitario en maquila (campo numérico → line 31)."""
    from models.ventas_editar import editar_venta
    id_art = venta_maquila["id_articulo"]
    result = editar_venta(
        id_venta=venta_maquila["id_venta"],
        fecha_estimada=None,
        nuevos_articulos=[],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[],
        eliminaciones_servicio=[],
        id_usuario=usuario_admin["id_usuario"],
        ediciones_articulo={id_art: {"precio_unitario": "60.00"}},
    )
    assert float(result["total_nuevo"]) == 600.0


def test_editar_venta_nuevo_articulo_tipo_incorrecto_raises(venta_pendiente, usuario_admin, servicio_calzado):
    """Line 313: nuevo artículo con tipo incorrecto para el negocio."""
    from models.ventas_editar import editar_venta
    with pytest.raises(ValueError, match="solo permite"):
        editar_venta(
            id_venta=venta_pendiente["id_venta"],
            fecha_estimada=None,
            nuevos_articulos=[{
                "tipo_articulo": "maquila",
                "datos": {"tipo": "Playera", "cantidad": "1", "precio_unitario": "50.00"},
                "servicios": [],
            }],
            nuevos_servicios_por_articulo=[],
            ediciones_servicio=[],
            eliminaciones_servicio=[],
            id_usuario=usuario_admin["id_usuario"],
        )


def test_editar_venta_agrega_nuevo_articulo_calzado(venta_pendiente, usuario_admin, servicio_calzado):
    """Lines 311-322: agregar artículo calzado válido a venta existente."""
    from models.ventas_editar import editar_venta
    sid = servicio_calzado["id_servicio"]
    result = editar_venta(
        id_venta=venta_pendiente["id_venta"],
        fecha_estimada=None,
        nuevos_articulos=[{
            "tipo_articulo": "calzado",
            "datos": {"tipo": "Bota", "marca": "Timberland", "material": "Piel", "color_base": "Cafe"},
            "servicios": [{"id_servicio": sid, "precio_aplicado": "100.00"}],
        }],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[],
        eliminaciones_servicio=[],
        id_usuario=usuario_admin["id_usuario"],
    )
    assert float(result["total_nuevo"]) == 250.0


def test_editar_venta_agrega_servicio_nuevo_a_articulo(venta_pendiente, usuario_admin, db_conn):
    """Lines 324-356: agregar nuevo servicio a artículo calzado existente."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        "INSERT INTO servicio (id_negocio, nombre, precio, activo) VALUES (1, 'ExtraSrv_pytest', 75.00, 1)"
    )
    db_conn.commit()
    id_srv_nuevo = cursor.lastrowid
    cursor.close()
    try:
        result = editar_venta(
            id_venta=venta_pendiente["id_venta"],
            fecha_estimada=None,
            nuevos_articulos=[],
            nuevos_servicios_por_articulo=[{
                "id_articulo": id_art,
                "servicios": [{"id_servicio": id_srv_nuevo, "precio_aplicado": "75.00"}],
            }],
            ediciones_servicio=[],
            eliminaciones_servicio=[],
            id_usuario=usuario_admin["id_usuario"],
        )
        assert float(result["total_nuevo"]) == 225.0
    finally:
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM articulo_servicio WHERE id_servicio = %s", (id_srv_nuevo,))
        cursor.execute("DELETE FROM servicios_historial WHERE id_servicio = %s", (id_srv_nuevo,))
        cursor.execute("DELETE FROM servicio WHERE id_servicio = %s", (id_srv_nuevo,))
        db_conn.commit()
        cursor.close()


def test_editar_venta_agrega_servicio_nuevo_a_confeccion(venta_confeccion, usuario_admin, db_conn):
    """Lines 352-354: servicio agregado a confeccion multiplica por cantidad."""
    from models.ventas_editar import editar_venta
    id_art = venta_confeccion["id_articulo"]
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute(
        "INSERT INTO servicio (id_negocio, nombre, precio, activo) VALUES (2, 'ExtraSrvConf_pytest', 100.00, 1)"
    )
    db_conn.commit()
    id_srv_nuevo = cursor.lastrowid
    cursor.close()
    try:
        result = editar_venta(
            id_venta=venta_confeccion["id_venta"],
            fecha_estimada=None,
            nuevos_articulos=[],
            nuevos_servicios_por_articulo=[{
                "id_articulo": id_art,
                "servicios": [{"id_servicio": id_srv_nuevo, "precio_aplicado": "100.00"}],
            }],
            ediciones_servicio=[],
            eliminaciones_servicio=[],
            id_usuario=usuario_admin["id_usuario"],
        )
        assert float(result["total_nuevo"]) == 600.0
    finally:
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM articulo_servicio WHERE id_servicio = %s", (id_srv_nuevo,))
        cursor.execute("DELETE FROM servicios_historial WHERE id_servicio = %s", (id_srv_nuevo,))
        cursor.execute("DELETE FROM servicio WHERE id_servicio = %s", (id_srv_nuevo,))
        db_conn.commit()
        cursor.close()


def test_editar_venta_agrega_servicio_duplicado_raises(venta_pendiente, usuario_admin):
    """Lines 342-346: agregar servicio ya existente en artículo lanza ValueError."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    id_srv = venta_pendiente["id_servicio"]
    with pytest.raises(ValueError, match="ya está asignado"):
        editar_venta(
            id_venta=venta_pendiente["id_venta"],
            fecha_estimada=None,
            nuevos_articulos=[],
            nuevos_servicios_por_articulo=[{
                "id_articulo": id_art,
                "servicios": [{"id_servicio": id_srv, "precio_aplicado": "150.00"}],
            }],
            ediciones_servicio=[],
            eliminaciones_servicio=[],
            id_usuario=usuario_admin["id_usuario"],
        )


def test_editar_venta_agrega_servicio_a_maquila_raises(venta_maquila, usuario_admin, servicio_calzado):
    """Line 336: artículo maquila no puede recibir servicios."""
    from models.ventas_editar import editar_venta
    id_art = venta_maquila["id_articulo"]
    with pytest.raises(ValueError, match="calzado o confección"):
        editar_venta(
            id_venta=venta_maquila["id_venta"],
            fecha_estimada=None,
            nuevos_articulos=[],
            nuevos_servicios_por_articulo=[{
                "id_articulo": id_art,
                "servicios": [{"id_servicio": servicio_calzado["id_servicio"], "precio_aplicado": "50.00"}],
            }],
            ediciones_servicio=[],
            eliminaciones_servicio=[],
            id_usuario=usuario_admin["id_usuario"],
        )


def test_editar_venta_total_menor_pagado_raises(venta_pendiente, usuario_admin, db_conn):
    """Line 366: total_nuevo menor al total_pagado lanza ValueError."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    id_srv = venta_pendiente["id_servicio"]
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO pago_venta (id_venta, monto, fecha_pago, tipo_pago, id_usuario_cobro)"
        " VALUES (%s, 9999.00, NOW(), 'efectivo', %s)",
        (venta_pendiente["id_venta"], usuario_admin["id_usuario"]),
    )
    db_conn.commit()
    cursor.close()
    try:
        with pytest.raises(ValueError, match="menor al total"):
            editar_venta(
                id_venta=venta_pendiente["id_venta"],
                fecha_estimada=None,
                nuevos_articulos=[],
                nuevos_servicios_por_articulo=[],
                ediciones_servicio=[],
                eliminaciones_servicio=[{"id_articulo": id_art, "id_servicio": id_srv}],
                id_usuario=usuario_admin["id_usuario"],
            )
    finally:
        cursor = db_conn.cursor()
        cursor.execute(
            "DELETE FROM pago_venta WHERE id_venta = %s AND monto = 9999.00",
            (venta_pendiente["id_venta"],),
        )
        db_conn.commit()
        cursor.close()


def test_editar_venta_info_srv_inexistente_skip(venta_pendiente, usuario_admin):
    """Line 191: _info_srv retorna None → edición de servicio es ignorada."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    result = editar_venta(
        id_venta=venta_pendiente["id_venta"],
        fecha_estimada="2031-06-01 10:00:00",
        nuevos_articulos=[],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[{"id_articulo": id_art, "id_servicio": 999999, "precio_aplicado": Decimal("200.00")}],
        eliminaciones_servicio=[],
        id_usuario=usuario_admin["id_usuario"],
    )
    assert "total_nuevo" in result


def test_editar_venta_elimina_servicio_inexistente_skip(venta_pendiente, usuario_admin):
    """Line 168: eliminar servicio que no existe en artículo → continue."""
    from models.ventas_editar import editar_venta
    id_art = venta_pendiente["id_articulo"]
    result = editar_venta(
        id_venta=venta_pendiente["id_venta"],
        fecha_estimada="2031-06-01 10:00:00",
        nuevos_articulos=[],
        nuevos_servicios_por_articulo=[],
        ediciones_servicio=[],
        eliminaciones_servicio=[{"id_articulo": id_art, "id_servicio": 999999}],
        id_usuario=usuario_admin["id_usuario"],
    )
    assert "total_nuevo" in result


def test_editar_venta_campo_numerico_invalido_raises(venta_confeccion, usuario_admin):
    """Lines 245-246: campo numérico con valor no parseable → invalido=True → ValueError."""
    from models.ventas_editar import editar_venta
    id_art = venta_confeccion["id_articulo"]
    with pytest.raises(ValueError):
        editar_venta(
            id_venta=venta_confeccion["id_venta"],
            fecha_estimada=None,
            nuevos_articulos=[],
            nuevos_servicios_por_articulo=[],
            ediciones_servicio=[],
            eliminaciones_servicio=[],
            id_usuario=usuario_admin["id_usuario"],
            ediciones_articulo={id_art: {"cantidad": "abc"}},
        )


def test_editar_venta_articulo_externo_no_pertenece_raises(venta_pendiente, usuario_admin, servicio_calzado):
    """Line 334: articulo_ex no pertenece a la venta → ValueError."""
    from models.ventas_editar import editar_venta
    with pytest.raises(ValueError, match="no pertenece"):
        editar_venta(
            id_venta=venta_pendiente["id_venta"],
            fecha_estimada=None,
            nuevos_articulos=[],
            nuevos_servicios_por_articulo=[{
                "id_articulo": 999999,
                "servicios": [{"id_servicio": servicio_calzado["id_servicio"], "precio_aplicado": "50.00"}],
            }],
            ediciones_servicio=[],
            eliminaciones_servicio=[],
            id_usuario=usuario_admin["id_usuario"],
        )
