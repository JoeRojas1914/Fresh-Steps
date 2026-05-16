from clientes import (
    buscar_clientes,
    contar_clientes,
    obtener_cliente_por_id,
    obtener_clientes,
    crear_cliente,
    actualizar_cliente,
    eliminar_cliente,
    restaurar_cliente,
    obtener_historial_cliente
)

from pagos import obtener_pagos_venta
from negocio import obtener_negocios
from ventas import contar_ventas_cliente, obtener_detalles_venta, obtener_ventas_cliente


def listar_clientes_service(
    q: str = "",
    pagina: int = 1,
    por_pagina: int = 10,
    incluir_eliminados: bool = False,
) -> dict:
    offset = (pagina - 1) * por_pagina
    total = contar_clientes(q, incluir_eliminados)
    clientes = obtener_clientes(q, por_pagina, offset, incluir_eliminados)
    total_paginas = (total + por_pagina - 1) // por_pagina
    return {
        "clientes":       clientes,
        "total_paginas":  total_paginas,
        "total_clientes": total,
    }


def guardar_cliente_service(form: dict, id_usuario: int, api: bool = False) -> str | dict:
    id_cliente = form.get("id_cliente")

    nombre    = form.get("nombre", "").strip()
    apellido  = form.get("apellido", "").strip()
    correo    = form.get("correo")
    telefono  = form.get("telefono")
    direccion = form.get("direccion")

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

    offset = (pagina - 1) * pedidos_por_pagina

    cliente       = obtener_cliente_por_id(id_cliente)
    total_pedidos = contar_ventas_cliente(id_cliente, id_negocio, fecha_inicio, fecha_fin)
    total_paginas = (total_pedidos + pedidos_por_pagina - 1) // pedidos_por_pagina
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
        total_pagado = sum(float(pg["monto"]) for pg in pagos)

        p["detalles"]       = detalles
        p["pagos"]          = pagos
        p["total_pagado"]   = total_pagado
        p["saldo_pendiente"] = float(p["total"]) - total_pagado

    negocios = obtener_negocios()

    return {
        "cliente":       cliente,
        "total_pedidos": total_pedidos,
        "pedidos":       pedidos,
        "negocios":      negocios,
        "pagina":        pagina,
        "total_paginas": total_paginas,
    }
