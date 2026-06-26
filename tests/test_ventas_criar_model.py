"""
Tests para models/ventas_crear.py.
Cubre las ramas no alcanzadas por los tests de servicio:
 - _resolver_precio: InvalidOperation y precio <= 0 (fetch desde BD)
 - _insertar_calzado / _insertar_confeccion sin servicios
 - crear_venta: descuento aplicado y total clampeado a 0
"""
import pytest
from decimal import Decimal


def _cleanup(db_conn, id_venta):
    cursor = db_conn.cursor()
    cursor.execute(
        "DELETE FROM articulo_servicio WHERE id_articulo IN "
        "(SELECT id_articulo FROM articulo WHERE id_venta = %s)",
        (id_venta,),
    )
    for tabla in ("articulo_calzado", "articulo_confeccion", "articulo_maquila"):
        cursor.execute(
            f"DELETE FROM {tabla} WHERE id_articulo IN "
            f"(SELECT id_articulo FROM articulo WHERE id_venta = %s)",
            (id_venta,),
        )
    cursor.execute("DELETE FROM articulo        WHERE id_venta = %s", (id_venta,))
    cursor.execute("DELETE FROM pago_venta      WHERE id_venta = %s", (id_venta,))
    cursor.execute("DELETE FROM venta_historial WHERE id_venta = %s", (id_venta,))
    cursor.execute("DELETE FROM venta           WHERE id_venta = %s", (id_venta,))
    db_conn.commit()
    cursor.close()


# ============================================================
# _insertar_calzado sin servicios (line 38)
# ============================================================

def test_insertar_calzado_sin_servicios_raises():
    from models.ventas_crear import _insertar_calzado
    with pytest.raises(ValueError, match="sin servicios"):
        _insertar_calzado(None, 999999, {"datos": {}, "servicios": []})


# ============================================================
# _insertar_confeccion sin servicios (line 54)
# ============================================================

def test_insertar_confeccion_sin_servicios_raises():
    from models.ventas_crear import _insertar_confeccion
    with pytest.raises(ValueError, match="sin servicios"):
        _insertar_confeccion(None, 999999, {"datos": {}, "servicios": []})


# ============================================================
# _resolver_precio: InvalidOperation (lines 10-11) + precio<=0 fetch BD (lines 14-19)
# ============================================================

def test_resolver_precio_invalido_usa_precio_bd(servicio_calzado, cliente_test, usuario_admin, db_conn):
    """precio_aplicado='abc' → InvalidOperation → precio=0 → fetch desde BD."""
    from models.ventas_crear import crear_venta
    id_venta = crear_venta(
        id_negocio=1,
        id_cliente=cliente_test["id_cliente"],
        fecha_estimada="2031-01-01 10:00:00",
        aplica_descuento=False,
        cantidad_descuento=None,
        articulos=[{
            "tipo_articulo": "calzado",
            "datos": {
                "tipo": "Tenis", "marca": "Adidas",
                "material": "Cuero", "color_base": "Negro",
            },
            "servicios": [{
                "id_servicio": servicio_calzado["id_servicio"],
                "precio_aplicado": "abc",
            }],
        }],
        id_usuario_creo=usuario_admin["id_usuario"],
    )
    assert id_venta is not None
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT total FROM venta WHERE id_venta = %s", (id_venta,))
    row = cursor.fetchone()
    cursor.close()
    assert Decimal(str(row["total"])) == Decimal("150.00")
    _cleanup(db_conn, id_venta)


# ============================================================
# crear_venta con descuento aplicado (lines 126-127)
# ============================================================

def test_crear_venta_con_descuento(servicio_calzado, cliente_test, usuario_admin, db_conn):
    """aplica_descuento=True, cantidad_descuento=50 → 150-50=100."""
    from models.ventas_crear import crear_venta
    id_venta = crear_venta(
        id_negocio=1,
        id_cliente=cliente_test["id_cliente"],
        fecha_estimada="2031-01-01 10:00:00",
        aplica_descuento=True,
        cantidad_descuento=50,
        articulos=[{
            "tipo_articulo": "calzado",
            "datos": {
                "tipo": "Tenis", "marca": "Adidas",
                "material": "Cuero", "color_base": "Negro",
            },
            "servicios": [{
                "id_servicio": servicio_calzado["id_servicio"],
                "precio_aplicado": "150.00",
            }],
        }],
        id_usuario_creo=usuario_admin["id_usuario"],
    )
    assert id_venta is not None
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT total FROM venta WHERE id_venta = %s", (id_venta,))
    row = cursor.fetchone()
    cursor.close()
    assert Decimal(str(row["total"])) == Decimal("100.00")
    _cleanup(db_conn, id_venta)


# ============================================================
# crear_venta descuento excesivo → total clampeado a 0 (lines 128-129)
# ============================================================

def test_crear_venta_tipo_articulo_incorrecto_raises(cliente_test, usuario_admin):
    """Line 113: tipo_articulo no coincide con el tipo del negocio → Exception."""
    from models.ventas_crear import crear_venta
    with pytest.raises(ValueError, match="solo permite"):
        crear_venta(
            id_negocio=1,
            id_cliente=cliente_test["id_cliente"],
            fecha_estimada="2031-01-01 10:00:00",
            aplica_descuento=False,
            cantidad_descuento=None,
            articulos=[{
                "tipo_articulo": "maquila",
                "datos": {"tipo": "Playera", "cantidad": "1", "precio_unitario": "50.00"},
                "servicios": [],
            }],
            id_usuario_creo=usuario_admin["id_usuario"],
        )


def test_crear_venta_descuento_excesivo_clampea_a_cero(servicio_calzado, cliente_test, usuario_admin, db_conn):
    """cantidad_descuento=9999 → total<0 → total=0."""
    from models.ventas_crear import crear_venta
    id_venta = crear_venta(
        id_negocio=1,
        id_cliente=cliente_test["id_cliente"],
        fecha_estimada="2031-01-01 10:00:00",
        aplica_descuento=True,
        cantidad_descuento=9999,
        articulos=[{
            "tipo_articulo": "calzado",
            "datos": {
                "tipo": "Tenis", "marca": "Adidas",
                "material": "Cuero", "color_base": "Negro",
            },
            "servicios": [{
                "id_servicio": servicio_calzado["id_servicio"],
                "precio_aplicado": "150.00",
            }],
        }],
        id_usuario_creo=usuario_admin["id_usuario"],
    )
    assert id_venta is not None
    cursor = db_conn.cursor(dictionary=True)
    cursor.execute("SELECT total FROM venta WHERE id_venta = %s", (id_venta,))
    row = cursor.fetchone()
    cursor.close()
    assert Decimal(str(row["total"])) == Decimal("0.00")
    _cleanup(db_conn, id_venta)
