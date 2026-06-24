from decimal import Decimal

from utils import calcular_paginacion
from validators import validar_nombre, validar_correo, validar_telefono
from models.clientes import (
    buscar_clientes,
    contar_clientes,
    contar_pedidos_por_cliente,
    obtener_cliente_por_id,
    obtener_clientes,
    crear_cliente,
    actualizar_cliente,
    eliminar_cliente,
    restaurar_cliente,
    obtener_historial_cliente
)

from models.pagos import obtener_pagos_venta
from models.negocio import obtener_negocios
from models.ventas import contar_ventas_cliente, obtener_detalles_venta, obtener_ventas_cliente
from models.ventas_detalles import obtener_kpis_cliente


def listar_clientes_service(
    q: str = "",
    pagina: int = 1,
    por_pagina: int = 10,
    incluir_eliminados: bool = False,
) -> dict:
    total = contar_clientes(q, incluir_eliminados)
    offset, total_paginas = calcular_paginacion(total, pagina, por_pagina)
    clientes = obtener_clientes(q, por_pagina, offset, incluir_eliminados)

    ids = [c["id_cliente"] for c in clientes]
    pedidos_map = contar_pedidos_por_cliente(ids)
    for c in clientes:
        c["total_pedidos"] = pedidos_map.get(c["id_cliente"], 0)

    return {
        "clientes":       clientes,
        "total_paginas":  total_paginas,
        "total_clientes": total,
    }


def guardar_cliente_service(form: dict, id_usuario: int, api: bool = False) -> str | dict:
    id_cliente = form.get("id_cliente")

    nombre    = validar_nombre(form.get("nombre"), "Nombre")
    apellido  = validar_nombre(form.get("apellido"), "Apellido")
    correo    = validar_correo(form.get("correo"))
    telefono  = validar_telefono(form.get("telefono"))
    direccion = form.get("direccion", "").strip() or None

    if id_cliente:
        actualizar_cliente(id_cliente, nombre, apellido, correo, telefono, direccion, id_usuario)
        return "actualizado"

    nuevo_id = crear_cliente(nombre, apellido, correo, telefono, direccion, id_usuario)

    if api:
        return {
            "id_cliente": nuevo_id,
            "nombre":     nombre,
            "apellido":   apellido,
        }

    return "creado"


def eliminar_cliente_service(id_cliente: int, id_usuario: int) -> bool:
    return eliminar_cliente(id_cliente, id_usuario)


def restaurar_cliente_service(id_cliente: int, id_usuario: int) -> None:
    restaurar_cliente(id_cliente, id_usuario)


def obtener_historial_cliente_service(id_cliente: int) -> list[dict]:
    return obtener_historial_cliente(id_cliente)


def buscar_clientes_service(q: str) -> list[dict]:
    if not q:
        return []
    return buscar_clientes(q)


def obtener_cliente_detalle_service(
    id_cliente: int,
    filtros: dict,
    pedidos_por_pagina: int = 5,
) -> dict:
    id_negocio   = filtros.get("id_negocio")
    fecha_inicio = filtros.get("fecha_inicio")
    fecha_fin    = filtros.get("fecha_fin")
    pagina       = int(filtros.get("pagina", 1))

    cliente       = obtener_cliente_por_id(id_cliente)
    total_pedidos = contar_ventas_cliente(id_cliente, id_negocio, fecha_inicio, fecha_fin)
    offset, total_paginas = calcular_paginacion(total_pedidos, pagina, pedidos_por_pagina)
    pedidos       = obtener_ventas_cliente(
        id_cliente, id_negocio, fecha_inicio, fecha_fin,
        pedidos_por_pagina, offset
    )

    ids_venta   = [p["id_venta"] for p in pedidos]
    detalles_map = obtener_detalles_venta(ids_venta)
    pagos_map    = obtener_pagos_venta(ids_venta)

    for p in pedidos:
        detalles     = detalles_map.get(p["id_venta"], [])
        pagos        = pagos_map.get(p["id_venta"], [])
        total_pagado = sum(Decimal(str(pg["monto"])) for pg in pagos)

        p["detalles"]        = detalles
        p["pagos"]           = pagos
        p["total_pagado"]    = total_pagado
        p["saldo_pendiente"] = Decimal(str(p["total"])) - total_pagado

    negocios = obtener_negocios()
    kpis     = obtener_kpis_cliente(id_cliente)

    return {
        "cliente":       cliente,
        "total_pedidos": total_pedidos,
        "pedidos":       pedidos,
        "negocios":      negocios,
        "pagina":        pagina,
        "total_paginas": total_paginas,
        "kpis":          kpis,
    }


def exportar_clientes_service(incluir_eliminados: bool) -> tuple[list, dict]:
    from config import MAX_FILAS_EXPORTAR
    clientes    = obtener_clientes(limit=MAX_FILAS_EXPORTAR, offset=0, incluir_eliminados=incluir_eliminados)
    ids         = [cl["id_cliente"] for cl in clientes]
    pedidos_map = contar_pedidos_por_cliente(ids)
    return clientes, pedidos_map


def exportar_cliente_service(
    id_cliente: int,
    id_negocio=None,
    fecha_inicio=None,
    fecha_fin=None,
) -> tuple[dict, list, dict, dict]:
    from config import MAX_FILAS_EXPORTAR
    cliente      = obtener_cliente_por_id(id_cliente)
    pedidos      = obtener_ventas_cliente(id_cliente, id_negocio, fecha_inicio, fecha_fin, limit=MAX_FILAS_EXPORTAR, offset=0)
    ids_venta    = [p["id_venta"] for p in pedidos]
    detalles_map = obtener_detalles_venta(ids_venta)
    pagos_map    = obtener_pagos_venta(ids_venta)
    return cliente, pedidos, detalles_map, pagos_map
