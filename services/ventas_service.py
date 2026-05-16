from datetime import date

from ventas import (
    eliminar_venta,
    marcar_entregada,
    marcar_como_lista,
    obtener_venta,
    obtener_ventas_listas,
    obtener_detalles_venta,
    obtener_entregas_pendientes,
    obtener_historial_ventas,
    contar_historial_ventas,
    crear_venta,
    TIPOS_POR_NEGOCIO,
)

from pagos import (
    obtener_pagos_venta,
    registrar_pago_final_db,
    registrar_pago,
)

from negocio import obtener_negocios


def listar_ventas_listas_service(id_negocio: int | None = None) -> dict:
    ventas   = obtener_ventas_listas(id_negocio)
    negocios = obtener_negocios()

    ids_venta    = [v["id_venta"] for v in ventas]
    detalles_map = obtener_detalles_venta(ids_venta)
    pagos_map    = obtener_pagos_venta(ids_venta)

    ventas_con_detalles = []

    for v in ventas:
        detalles     = detalles_map.get(v["id_venta"], [])
        pagos        = pagos_map.get(v["id_venta"], [])
        total_pagado = sum(float(p["monto"]) for p in pagos)
        total        = float(v.get("total") or 0)

        v["detalles"]        = detalles
        v["pagos"]           = pagos
        v["total"]           = total
        v["total_pagado"]    = total_pagado
        v["saldo_pendiente"] = max(total - total_pagado, 0)
        v["tiene_pagos"]     = total_pagado > 0
        v["esta_pagada"]     = v["saldo_pendiente"] == 0

        ventas_con_detalles.append(v)

    return {
        "ventas":   ventas_con_detalles,
        "negocios": negocios,
        "hoy":      date.today(),
    }


def listar_entregas_pendientes_service(id_negocio: int | None = None) -> dict:
    ventas   = obtener_entregas_pendientes(id_negocio)
    negocios = obtener_negocios()

    ids_venta    = [v["id_venta"] for v in ventas]
    detalles_map = obtener_detalles_venta(ids_venta)

    ventas_con_detalles = []

    for v in ventas:
        v["detalles"] = detalles_map.get(v["id_venta"], [])
        ventas_con_detalles.append(v)

    return {
        "ventas":   ventas_con_detalles,
        "negocios": negocios,
        "hoy":      date.today(),
    }


def registrar_pago_final_service(data: dict, id_usuario: int) -> tuple[bool, str]:
    id_venta   = data.get("id_venta")
    monto      = data.get("monto")
    metodo_pago = data.get("metodo_pago")

    if not id_venta or not monto or not metodo_pago:
        return False, "Datos incompletos para el pago final"

    registrar_pago_final_db(
        id_venta=id_venta,
        monto=monto,
        metodo_pago=metodo_pago,
        id_usuario=id_usuario
    )

    marcar_entregada(id_venta, id_usuario)

    return True, "Pago final registrado y venta marcada como entregada"


def eliminar_venta_service(id_venta: int, id_usuario: int | None = None) -> tuple[bool, str]:
    venta = obtener_venta(id_venta)
    if not venta:
        return False, "La venta no existe"
    eliminar_venta(id_venta, id_usuario)
    return True, "Venta eliminada correctamente"


def guardar_venta_service(form: dict, id_usuario_creo: int) -> tuple[int | None, str | None]:
    try:
        id_negocio = int(form["id_negocio"])
    except (KeyError, ValueError):
        return None, "Negocio inválido."

    id_cliente     = form.get("id_cliente") or None
    fecha_estimada = form.get("fecha_estimada") or None
    tipo_pago      = form.get("tipo_pago")

    prepago = form.get("prepago") == "si"
    try:
        monto_prepago = float(form.get("monto_prepago") or 0) if prepago else 0
    except (ValueError, TypeError):
        return None, "El monto del prepago no es válido."

    aplica_descuento = form.get("aplica_descuento") == "si"
    try:
        cantidad_descuento = float(form.get("cantidad_descuento") or 0) if aplica_descuento else 0
    except (ValueError, TypeError):
        return None, "El monto del descuento no es válido."

    tipo_permitido = TIPOS_POR_NEGOCIO.get(id_negocio)

    try:
        articulos = []
        i = 0
        while True:
            tipo_articulo = form.get(f"articulos[{i}][tipo_articulo]")
            if not tipo_articulo:
                break

            if tipo_permitido and tipo_articulo != tipo_permitido:
                return None, f"Este negocio solo permite artículos tipo: {tipo_permitido}"

            comentario = form.get(f"articulos[{i}][comentario]")

            if tipo_articulo == "calzado":
                datos = {
                    "tipo":             form.get(f"articulos[{i}][tipo]"),
                    "marca":            form.get(f"articulos[{i}][marca]"),
                    "material":         form.get(f"articulos[{i}][material]"),
                    "color_base":       form.get(f"articulos[{i}][color_base]"),
                    "color_secundario": form.get(f"articulos[{i}][color_secundario]"),
                    "color_agujetas":   form.get(f"articulos[{i}][color_agujetas]"),
                }
                servicios = _parsear_servicios(form, i)
                articulos.append({
                    "tipo_articulo": "calzado", "datos": datos,
                    "servicios": servicios, "comentario": comentario,
                })

            elif tipo_articulo == "confeccion":
                datos = {
                    "tipo":             form.get(f"articulos[{i}][tipo]"),
                    "marca":            form.get(f"articulos[{i}][marca]"),
                    "material":         form.get(f"articulos[{i}][material]"),
                    "color_base":       form.get(f"articulos[{i}][color_base]"),
                    "color_secundario": form.get(f"articulos[{i}][color_secundario]"),
                    "cantidad":         int(form.get(f"articulos[{i}][cantidad]") or 1),
                    "agujetas":         form.get(f"articulos[{i}][agujetas]") == "1",
                }
                servicios = _parsear_servicios(form, i)
                articulos.append({
                    "tipo_articulo": "confeccion", "datos": datos,
                    "servicios": servicios, "comentario": comentario,
                })

            elif tipo_articulo == "maquila":
                datos = {
                    "tipo":            form.get(f"articulos[{i}][tipo]"),
                    "cantidad":        int(form.get(f"articulos[{i}][cantidad]") or 1),
                    "precio_unitario": float(form.get(f"articulos[{i}][precio_unitario]") or 0),
                }
                articulos.append({
                    "tipo_articulo": "maquila", "datos": datos,
                    "comentario": comentario,
                })

            i += 1
    except (ValueError, TypeError):
        return None, "Datos de artículos inválidos (cantidad o precio no numérico)."

    if not id_cliente or not fecha_estimada:
        return None, "Faltan datos obligatorios (cliente, negocio, fecha estimada o tipo de pago)."

    if not articulos:
        return None, "Debes agregar al menos 1 artículo."

    if id_negocio in (1, 2):
        for a in articulos:
            if not a.get("servicios"):
                return None, "Cada artículo debe tener al menos 1 servicio."
            for s in a["servicios"]:
                if not s.get("id_servicio"):
                    return None, "Servicio inválido (sin id)."
                if float(s.get("precio_aplicado") or 0) <= 0:
                    return None, "El precio aplicado debe ser mayor a 0."

    if id_negocio == 3:
        for a in articulos:
            if a.get("servicios"):
                return None, "Maquila no permite servicios."

    id_venta = crear_venta(
        id_negocio=id_negocio,
        id_cliente=id_cliente,
        fecha_estimada=fecha_estimada,
        aplica_descuento=aplica_descuento,
        cantidad_descuento=cantidad_descuento,
        articulos=articulos,
        id_usuario_creo=id_usuario_creo,
    )

    if prepago and monto_prepago > 0:
        if not tipo_pago:
            return None, "Debes seleccionar el tipo de pago del prepago."
        registrar_pago(
            id_venta=id_venta,
            monto=monto_prepago,
            tipo_pago=tipo_pago,
            id_usuario_cobro=id_usuario_creo,
        )

    return id_venta, None


def _parsear_servicios(form: dict, i: int) -> list[dict]:
    servicios = []
    j = 0
    while True:
        id_serv = form.get(f"articulos[{i}][servicios][{j}][id_servicio]")
        if not id_serv:
            break
        precio_ap = form.get(f"articulos[{i}][servicios][{j}][precio_aplicado]") or 0
        servicios.append({"id_servicio": int(id_serv), "precio_aplicado": float(precio_ap)})
        j += 1
    return servicios


POR_PAGINA_HISTORIAL = 20


def historial_ventas_service(
    id_negocio: int | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    pagina: int = 1,
    mostrar_eliminadas: bool = False,
    q: str | None = None,
) -> dict:
    offset          = (pagina - 1) * POR_PAGINA_HISTORIAL
    total_registros = contar_historial_ventas(
        id_negocio, fecha_inicio, fecha_fin, mostrar_eliminadas, q=q
    )
    total_paginas   = max(1, (total_registros + POR_PAGINA_HISTORIAL - 1) // POR_PAGINA_HISTORIAL)

    ventas   = obtener_historial_ventas(
        id_negocio, fecha_inicio, fecha_fin,
        limit=POR_PAGINA_HISTORIAL, offset=offset,
        mostrar_eliminadas=mostrar_eliminadas, q=q,
    )
    negocios = obtener_negocios()

    ids_venta    = [v["id_venta"] for v in ventas]
    detalles_map = obtener_detalles_venta(ids_venta)
    pagos_map    = obtener_pagos_venta(ids_venta)

    resultado = []
    for v in ventas:
        total        = float(v.get("total") or 0)
        total_pagado = float(v.get("total_pagado") or 0)

        v["detalles"]        = detalles_map.get(v["id_venta"], [])
        v["pagos"]           = pagos_map.get(v["id_venta"], [])
        v["total"]           = total
        v["total_pagado"]    = total_pagado
        v["saldo_pendiente"] = max(total - total_pagado, 0)
        v["esta_pagada"]     = v["saldo_pendiente"] == 0

        if v.get("eliminado"):
            v["estado"] = "eliminada"
        elif v.get("fecha_entrega"):
            v["estado"] = "entregada"
        elif v.get("fecha_lista"):
            v["estado"] = "lista"
        else:
            v["estado"] = "pendiente"

        resultado.append(v)

    return {
        "ventas":             resultado,
        "negocios":           negocios,
        "hoy":                date.today(),
        "id_negocio":         id_negocio,
        "fecha_inicio":       fecha_inicio,
        "fecha_fin":          fecha_fin,
        "pagina":             pagina,
        "total_paginas":      total_paginas,
        "total_registros":    total_registros,
        "mostrar_eliminadas": mostrar_eliminadas,
        "q":                  q,
    }


def marcar_lista_service(id_venta: int, id_usuario: int | None = None) -> bool:
    return marcar_como_lista(id_venta, id_usuario)

