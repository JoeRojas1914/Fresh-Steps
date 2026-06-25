from decimal import Decimal, InvalidOperation
from db import get_db
from .negocio import cargar_tipos_por_negocio
from .ventas_historial import registrar_historial_venta


def _resolver_precio(cursor, s):
    try:
        precio = Decimal(str(s.get("precio_aplicado") or "0"))
    except InvalidOperation:
        precio = Decimal("0")

    if precio <= 0:
        cursor.execute(
            "SELECT precio FROM servicio WHERE id_servicio = %s",
            (int(s["id_servicio"]),),
        )
        row = cursor.fetchone()
        precio = Decimal(str(row["precio"])) if row else Decimal("0")

    return precio


def _insertar_servicios(cursor, id_articulo: int, servicios: list) -> Decimal:
    total = Decimal("0.00")
    for s in servicios:
        precio = _resolver_precio(cursor, s)
        cursor.execute(
            "INSERT INTO articulo_servicio (id_articulo, id_servicio, precio_aplicado) VALUES (%s, %s, %s)",
            (id_articulo, int(s["id_servicio"]), precio),
        )
        total += precio
    return total


def _insertar_calzado(cursor, id_articulo: int, art: dict) -> Decimal:
    if not art.get("servicios"):
        raise Exception("Artículo de calzado sin servicios")
    d = art["datos"]
    cursor.execute("""
        INSERT INTO articulo_calzado (
            id_articulo, tipo, marca, material,
            color_base, color_secundario, color_agujetas
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        id_articulo, d["tipo"], d["marca"], d["material"],
        d["color_base"], d.get("color_secundario"), d.get("color_agujetas"),
    ))
    return _insertar_servicios(cursor, id_articulo, art["servicios"])


def _insertar_confeccion(cursor, id_articulo: int, art: dict) -> Decimal:
    if not art.get("servicios"):
        raise Exception("Artículo de confección sin servicios")
    d = art["datos"]
    cantidad = Decimal(str(d.get("cantidad", 1)))
    cursor.execute("""
        INSERT INTO articulo_confeccion (
            id_articulo, tipo, marca, material,
            color_base, color_secundario, cantidad
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        id_articulo, d["tipo"], d["marca"], d["material"],
        d["color_base"], d.get("color_secundario"), int(cantidad),
    ))
    return cantidad * _insertar_servicios(cursor, id_articulo, art["servicios"])


def _insertar_maquila(cursor, id_articulo: int, art: dict) -> Decimal:
    d = art["datos"]
    cantidad        = Decimal(str(d["cantidad"]))
    precio_unitario = Decimal(str(d["precio_unitario"]))
    cursor.execute(
        "INSERT INTO articulo_maquila (id_articulo, tipo, cantidad, precio_unitario) VALUES (%s, %s, %s, %s)",
        (id_articulo, d["tipo"], int(cantidad), precio_unitario),
    )
    return cantidad * precio_unitario


_INSERTADORES = {
    "calzado":    _insertar_calzado,
    "confeccion": _insertar_confeccion,
    "maquila":    _insertar_maquila,
}


def crear_venta(
    id_negocio,
    id_cliente,
    fecha_estimada,
    aplica_descuento,
    cantidad_descuento,
    articulos,
    id_usuario_creo,
):
    with get_db() as (_, cursor):
        cursor.execute("""
            INSERT INTO venta (
                id_negocio, id_cliente, fecha_recibo, fecha_estimada,
                aplica_descuento, cantidad_descuento, total, id_usuario_creo
            ) VALUES (%s, %s, NOW(), %s, %s, %s, 0, %s)
        """, (id_negocio, id_cliente, fecha_estimada,
              aplica_descuento, cantidad_descuento, id_usuario_creo))

        id_venta      = cursor.lastrowid
        total         = Decimal("0.00")
        tipos_negocio = cargar_tipos_por_negocio()

        for art in articulos:
            tipo_articulo = art["tipo_articulo"]
            tipo_esperado = tipos_negocio.get(id_negocio)
            if tipo_esperado and tipo_articulo != tipo_esperado:
                raise Exception(f"Tipo de artículo inválido. Este negocio solo permite: {tipo_esperado}")

            cursor.execute(
                "INSERT INTO articulo (id_venta, tipo_articulo, comentario) VALUES (%s, %s, %s)",
                (id_venta, tipo_articulo, art.get("comentario")),
            )
            id_articulo = cursor.lastrowid

            insertador = _INSERTADORES.get(tipo_articulo)
            if not insertador:  # pragma: no cover
                raise Exception(f"Tipo de artículo desconocido: {tipo_articulo}")
            total += insertador(cursor, id_articulo, art)

        if aplica_descuento and cantidad_descuento:
            total -= Decimal(str(cantidad_descuento))
            if total < 0:
                total = Decimal("0.00")

        cursor.execute(
            "UPDATE venta SET total = %s WHERE id_venta = %s",
            (str(total), id_venta),
        )

        registrar_historial_venta(cursor, id_venta, "CREADO", id_usuario_creo, None, {
            "id_negocio":     id_negocio,
            "id_cliente":     id_cliente,
            "fecha_estimada": str(fecha_estimada),
            "total":          float(total),
        })

        return id_venta
