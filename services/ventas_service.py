from datetime import date

from config import METODOS_PAGO_VALIDOS, POR_PAGINA_VENTAS_ACTIVAS
from models.ventas import (
    eliminar_venta,
    marcar_entregada,
    marcar_como_lista,
    revertir_lista,
    obtener_venta,
    obtener_ventas_listas,
    obtener_detalles_venta,
    obtener_entregas_pendientes,
    obtener_historial_ventas,
    contar_historial_ventas,
    contar_entregas_listas,
    contar_entregas_pendientes,
    crear_venta,
)

from models.pagos import (
    obtener_pagos_venta,
    registrar_pago_final_db,
    registrar_pago,
)

from models.negocio import obtener_negocios, cargar_tipos_por_negocio


def listar_ventas_listas_service(
    id_negocio: int | None = None,
    pagina: int = 1,
    id_venta: int | None = None,
) -> dict:
    offset          = (pagina - 1) * POR_PAGINA_VENTAS_ACTIVAS
    total_registros = contar_entregas_listas(id_negocio, id_venta)
    total_paginas   = max(
        1, (total_registros + POR_PAGINA_VENTAS_ACTIVAS - 1) // POR_PAGINA_VENTAS_ACTIVAS
    )

    ventas   = obtener_ventas_listas(
        id_negocio, id_venta=id_venta,
        limit=POR_PAGINA_VENTAS_ACTIVAS, offset=offset,
    )
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
        "ventas":          ventas_con_detalles,
        "negocios":        negocios,
        "hoy":             date.today(),
        "id_negocio":      id_negocio,
        "id_venta":        id_venta,
        "pagina":          pagina,
        "total_paginas":   total_paginas,
        "total_registros": total_registros,
    }


def listar_entregas_pendientes_service(
    id_negocio: int | None = None,
    pagina: int = 1,
    id_venta: int | None = None,
) -> dict:
    offset          = (pagina - 1) * POR_PAGINA_VENTAS_ACTIVAS
    total_registros = contar_entregas_pendientes(id_negocio, id_venta)
    total_paginas   = max(
        1, (total_registros + POR_PAGINA_VENTAS_ACTIVAS - 1) // POR_PAGINA_VENTAS_ACTIVAS
    )

    ventas   = obtener_entregas_pendientes(
        id_negocio, id_venta=id_venta,
        limit=POR_PAGINA_VENTAS_ACTIVAS, offset=offset,
    )
    negocios = obtener_negocios()

    ids_venta    = [v["id_venta"] for v in ventas]
    detalles_map = obtener_detalles_venta(ids_venta)

    ventas_con_detalles = []
    for v in ventas:
        v["detalles"] = detalles_map.get(v["id_venta"], [])
        ventas_con_detalles.append(v)

    return {
        "ventas":          ventas_con_detalles,
        "negocios":        negocios,
        "hoy":             date.today(),
        "id_negocio":      id_negocio,
        "id_venta":        id_venta,
        "pagina":          pagina,
        "total_paginas":   total_paginas,
        "total_registros": total_registros,
    }


def registrar_pago_final_service(data: dict, id_usuario: int) -> str:
    id_venta    = data.get("id_venta")
    monto       = data.get("monto")
    metodo_pago = data.get("metodo_pago")

    if not id_venta or not monto or not metodo_pago:
        raise ValueError("Datos incompletos para el pago final")

    if metodo_pago not in METODOS_PAGO_VALIDOS:
        raise ValueError(f"Método de pago no válido: '{metodo_pago}'")

    registrar_pago_final_db(
        id_venta=id_venta,
        monto=monto,
        metodo_pago=metodo_pago,
        id_usuario=id_usuario
    )

    marcar_entregada(id_venta, id_usuario)

    return "Pago final registrado y venta marcada como entregada"


def eliminar_venta_service(id_venta: int, id_usuario: int | None = None) -> None:
    venta = obtener_venta(id_venta)
    if not venta:
        raise ValueError("La venta no existe")
    eliminar_venta(id_venta, id_usuario)


def _parsear_prepago(form: dict) -> tuple[bool, float]:
    if form.get("prepago") != "si":
        return False, 0
    try:
        return True, float(form.get("monto_prepago") or 0)
    except (ValueError, TypeError):
        raise ValueError("El monto del prepago no es válido.")


def _parsear_descuento(form: dict) -> tuple[bool, float]:
    if form.get("aplica_descuento") != "si":
        return False, 0
    try:
        return True, float(form.get("cantidad_descuento") or 0)
    except (ValueError, TypeError):
        raise ValueError("El monto del descuento no es válido.")


def _parsear_articulos_form(form: dict, tipo_permitido: str | None) -> list:
    articulos: list = []
    try:
        i = 0
        while True:
            tipo_articulo = form.get(f"articulos[{i}][tipo_articulo]")
            if not tipo_articulo:
                break
            if tipo_permitido and tipo_articulo != tipo_permitido:
                raise ValueError(
                    f"Este negocio solo permite artículos tipo: {tipo_permitido}"
                )
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
                articulos.append({
                    "tipo_articulo": "calzado", "datos": datos,
                    "servicios": _parsear_servicios(form, i), "comentario": comentario,
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
                articulos.append({
                    "tipo_articulo": "confeccion", "datos": datos,
                    "servicios": _parsear_servicios(form, i), "comentario": comentario,
                })
            elif tipo_articulo == "maquila":
                datos = {
                    "tipo":            form.get(f"articulos[{i}][tipo]"),
                    "cantidad":        int(form.get(f"articulos[{i}][cantidad]") or 1),
                    "precio_unitario": float(form.get(f"articulos[{i}][precio_unitario]") or 0),
                }
                articulos.append({
                    "tipo_articulo": "maquila", "datos": datos, "comentario": comentario,
                })
            i += 1
    except ValueError:
        raise
    except TypeError:
        raise ValueError("Datos de artículos inválidos (cantidad o precio no numérico).")
    return articulos


def _validar_reglas_negocio(tipo_negocio: str | None, articulos: list) -> None:
    if tipo_negocio in ("calzado", "confeccion"):
        for a in articulos:
            if not a.get("servicios"):
                raise ValueError("Cada artículo debe tener al menos 1 servicio.")
            for s in a["servicios"]:
                if not s.get("id_servicio"):
                    raise ValueError("Servicio inválido (sin id).")
                if float(s.get("precio_aplicado") or 0) <= 0:
                    raise ValueError("El precio aplicado debe ser mayor a 0.")
    if tipo_negocio == "maquila":
        for a in articulos:
            if a.get("servicios"):
                raise ValueError("Maquila no permite servicios.")


def guardar_venta_service(form: dict, id_usuario_creo: int) -> int:
    try:
        id_negocio = int(form["id_negocio"])
    except (KeyError, ValueError):
        raise ValueError("Negocio inválido.")

    id_cliente     = form.get("id_cliente") or None
    fecha_estimada = form.get("fecha_estimada") or None

    prepago, monto_prepago   = _parsear_prepago(form)
    aplica_descuento, cantidad_descuento = _parsear_descuento(form)
    tipo_negocio = cargar_tipos_por_negocio().get(id_negocio)
    articulos = _parsear_articulos_form(form, tipo_negocio)

    if not id_cliente or not fecha_estimada:
        raise ValueError(
            "Faltan datos obligatorios (cliente, negocio, fecha estimada o tipo de pago)."
        )

    if not articulos:
        raise ValueError("Debes agregar al menos 1 artículo.")

    _validar_reglas_negocio(tipo_negocio, articulos)

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
        tipo_pago = form.get("tipo_pago")
        if not tipo_pago:
            raise ValueError("Debes seleccionar el tipo de pago del prepago.")
        registrar_pago(
            id_venta=id_venta,
            monto=monto_prepago,
            tipo_pago=tipo_pago,
            id_usuario_cobro=id_usuario_creo,
        )

    return id_venta


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


from config import POR_PAGINA_HISTORIAL_VENTAS as POR_PAGINA_HISTORIAL


def historial_ventas_service(
    id_negocio: int | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    pagina: int = 1,
    mostrar_eliminadas: bool = False,
    q: str | None = None,
    id_venta: int | None = None,
    estado: str | None = None,
) -> dict:
    offset          = (pagina - 1) * POR_PAGINA_HISTORIAL
    total_registros = contar_historial_ventas(
        id_negocio, fecha_inicio, fecha_fin, mostrar_eliminadas, q=q, id_venta=id_venta, estado=estado
    )
    total_paginas   = max(
        1, (total_registros + POR_PAGINA_HISTORIAL - 1) // POR_PAGINA_HISTORIAL
    )

    ventas   = obtener_historial_ventas(
        id_negocio, fecha_inicio, fecha_fin,
        limit=POR_PAGINA_HISTORIAL, offset=offset,
        mostrar_eliminadas=mostrar_eliminadas, q=q, id_venta=id_venta, estado=estado,
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
        "id_venta":           id_venta,
        "estado":             estado,
    }


def marcar_lista_service(id_venta: int, id_usuario: int | None = None) -> bool:
    return marcar_como_lista(id_venta, id_usuario)


def revertir_lista_service(id_venta: int, id_usuario: int | None = None) -> bool:
    return revertir_lista(id_venta, id_usuario)

