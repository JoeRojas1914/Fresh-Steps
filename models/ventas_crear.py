from decimal import Decimal, InvalidOperation
from datetime import datetime
from db import get_db
from .ventas_historial import registrar_historial_venta


TIPOS_POR_NEGOCIO = {
    1: "calzado",
    2: "confeccion",
    3: "maquila",
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
                id_negocio,
                id_cliente,
                fecha_recibo,
                fecha_estimada,
                aplica_descuento,
                cantidad_descuento,
                total,
                id_usuario_creo
            )
            VALUES (%s, %s, %s, %s, %s, %s, 0, %s)
        """, (
            id_negocio,
            id_cliente,
            datetime.now(),
            fecha_estimada,
            aplica_descuento,
            cantidad_descuento,
            id_usuario_creo,
        ))

        id_venta = cursor.lastrowid
        total = Decimal("0.00")

        for art in articulos:
            tipo_articulo = art["tipo_articulo"]
            tipo_esperado = TIPOS_POR_NEGOCIO.get(id_negocio)

            if tipo_esperado and tipo_articulo != tipo_esperado:
                raise Exception(
                    f"Tipo de artículo inválido. Este negocio solo permite: {tipo_esperado}"
                )

            cursor.execute("""
                INSERT INTO articulo (id_venta, tipo_articulo, comentario)
                VALUES (%s, %s, %s)
            """, (id_venta, tipo_articulo, art.get("comentario")))

            id_articulo = cursor.lastrowid

            if tipo_articulo == "calzado":
                d = art["datos"]
                cursor.execute("""
                    INSERT INTO articulo_calzado (
                        id_articulo, tipo, marca, material,
                        color_base, color_secundario, color_agujetas
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    id_articulo, d["tipo"], d["marca"], d["material"],
                    d["color_base"], d.get("color_secundario"), d.get("color_agujetas"),
                ))

                if not art.get("servicios"):
                    raise Exception("Artículo de calzado sin servicios")

                for s in art["servicios"]:
                    precio_aplicado = _resolver_precio(cursor, s)
                    cursor.execute("""
                        INSERT INTO articulo_servicio (id_articulo, id_servicio, precio_aplicado)
                        VALUES (%s, %s, %s)
                    """, (id_articulo, int(s["id_servicio"]), precio_aplicado))
                    total += precio_aplicado

            elif tipo_articulo == "confeccion":
                d = art["datos"]
                cantidad = Decimal(str(d.get("cantidad", 1)))
                cursor.execute("""
                    INSERT INTO articulo_confeccion (
                        id_articulo, tipo, marca, material,
                        color_base, color_secundario, cantidad, agujetas
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    id_articulo, d["tipo"], d["marca"], d["material"],
                    d["color_base"], d.get("color_secundario"), int(cantidad), d["agujetas"],
                ))

                if not art.get("servicios"):
                    raise Exception("Artículo de confección sin servicios")

                for s in art["servicios"]:
                    precio_aplicado = _resolver_precio(cursor, s)
                    cursor.execute("""
                        INSERT INTO articulo_servicio (id_articulo, id_servicio, precio_aplicado)
                        VALUES (%s, %s, %s)
                    """, (id_articulo, int(s["id_servicio"]), precio_aplicado))
                    total += cantidad * precio_aplicado

            elif tipo_articulo == "maquila":
                d = art["datos"]
                cantidad = Decimal(str(d["cantidad"]))
                precio_unitario = Decimal(str(d["precio_unitario"]))
                cursor.execute("""
                    INSERT INTO articulo_maquila (id_articulo, tipo, cantidad, precio_unitario)
                    VALUES (%s, %s, %s, %s)
                """, (id_articulo, d["tipo"], int(cantidad), precio_unitario))
                total += cantidad * precio_unitario

        if aplica_descuento and cantidad_descuento:
            total -= Decimal(str(cantidad_descuento))
            if total < 0:
                total = Decimal("0.00")

        cursor.execute(
            "UPDATE venta SET total = %s WHERE id_venta = %s",
            (str(total), id_venta),
        )

        registrar_historial_venta(cursor, id_venta, "CREADO", id_usuario_creo, None, {
            "id_negocio": id_negocio,
            "id_cliente": id_cliente,
            "fecha_estimada": str(fecha_estimada),
            "total": float(total),
        })

        return id_venta


def _resolver_precio(cursor, s):
    try:
        precio = Decimal(str(s.get("precio_aplicado") or "0"))
    except InvalidOperation:
        precio = Decimal("0")

    if precio <= 0:
        cursor.execute(
            "SELECT precio_base FROM servicio WHERE id_servicio = %s",
            (int(s["id_servicio"]),),
        )
        row = cursor.fetchone()
        precio = Decimal(str(row["precio_base"])) if row else Decimal("0")

    return precio
