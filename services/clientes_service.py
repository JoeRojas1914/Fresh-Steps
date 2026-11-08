from decimal import Decimal

from openpyxl import Workbook

from utils import a_entero, calcular_paginacion
from validators import validar_nombre, validar_correo, validar_telefono
from services.excel_helpers import (
    xl_cell, xl_row_bg, xl_titulo_hoja, xl_fila_headers,
    xl_col_widths, xl_badge_activo, build_excel_cliente,
)
from models.clientes import (
    buscar_clientes,
    contar_clientes,
    contar_pedidos_por_cliente,
    obtener_cliente_por_id,
    obtener_cliente_por_telefono,
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
    orden: str | None = None,
    direccion: str | None = None,
    id_negocio: list[int] | None = None,
) -> dict:
    """`id_negocio`: solo clientes con compras en esos negocios (y pedidos contados ahí)."""
    total = contar_clientes(q, incluir_eliminados, id_negocio=id_negocio)
    offset, total_paginas = calcular_paginacion(total, pagina, por_pagina)
    clientes = obtener_clientes(q, por_pagina, offset, incluir_eliminados,
                                orden=orden, direccion=direccion, id_negocio=id_negocio)

    ids = [c["id_cliente"] for c in clientes]
    pedidos_map = contar_pedidos_por_cliente(ids, id_negocio=id_negocio)
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

    if telefono:
        duplicado = obtener_cliente_por_telefono(telefono, excluir_id=id_cliente)
        if duplicado:
            raise ValueError(
                f"Ese teléfono ya está registrado a nombre de "
                f"{duplicado['nombre']} {duplicado['apellido']}"
            )

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


def obtener_cliente_service(id_cliente: int) -> dict | None:
    """Datos editables de un cliente activo (None si no existe o está eliminado)."""
    cliente = obtener_cliente_por_id(id_cliente)
    if not cliente or not cliente.get("activo"):
        return None
    return {
        "id_cliente": cliente["id_cliente"],
        "nombre":     cliente["nombre"],
        "apellido":   cliente["apellido"],
        "telefono":   cliente.get("telefono") or "",
        "correo":     cliente.get("correo") or "",
        "direccion":  cliente.get("direccion") or "",
    }


def buscar_clientes_service(q: str) -> list[dict]:
    if not q:
        return []
    return buscar_clientes(q)


def obtener_cliente_detalle_service(
    id_cliente: int,
    filtros: dict,
    pedidos_por_pagina: int = 5,
    negocios_kpis: list[int] | None = None,
) -> dict:
    """`filtros["id_negocio"]` puede ser uno o varios negocios.
    `negocios_kpis`: negocios que cuentan en los KPIs (None = todos)."""
    id_negocio   = filtros.get("id_negocio")
    fecha_inicio = filtros.get("fecha_inicio")
    fecha_fin    = filtros.get("fecha_fin")
    pagina       = a_entero(filtros.get("pagina") or "") or 1

    cliente       = obtener_cliente_por_id(id_cliente)
    total_pedidos = contar_ventas_cliente(id_cliente, id_negocio, fecha_inicio, fecha_fin)
    offset, total_paginas = calcular_paginacion(total_pedidos, pagina, pedidos_por_pagina)
    pedidos       = obtener_ventas_cliente(
        id_cliente, id_negocio, fecha_inicio, fecha_fin,
        pedidos_por_pagina, offset,
        orden=filtros.get("orden"), direccion=filtros.get("dir"),
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
    kpis     = obtener_kpis_cliente(id_cliente, negocios_kpis)

    return {
        "cliente":       cliente,
        "total_pedidos": total_pedidos,
        "pedidos":       pedidos,
        "negocios":      negocios,
        "pagina":        pagina,
        "total_paginas": total_paginas,
        "kpis":          kpis,
    }


def exportar_clientes_service(
    incluir_eliminados: bool,
    q: str | None = None,
    orden: str | None = None,
    direccion: str | None = None,
) -> tuple[list, dict]:
    from config import MAX_FILAS_EXPORTAR
    clientes    = obtener_clientes(q, limit=MAX_FILAS_EXPORTAR, offset=0,
                                   incluir_eliminados=incluir_eliminados,
                                   orden=orden, direccion=direccion)
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


# ── Exportaciones a Excel ────────────────────────────────────────────────────

def exportar_clientes_excel_service(
    incluir_eliminados: bool,
    q: str | None = None,
    orden: str | None = None,
    direccion: str | None = None,
) -> Workbook:
    clientes, pedidos_map = exportar_clientes_service(incluir_eliminados, q=q,
                                                      orden=orden, direccion=direccion)

    subtexto = "Incluye eliminados" if incluir_eliminados else "Solo clientes activos"
    if q:
        subtexto += f"  |  Búsqueda: {q}"

    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes"
    ws.freeze_panes = "A4"

    xl_titulo_hoja(ws, "Clientes — Fresh Steps", 7, subtexto)
    xl_fila_headers(ws, ["Nombre", "Apellido", "Teléfono", "Correo", "Dirección", "Estado", "Total pedidos"])

    for i, cl in enumerate(clientes):
        r  = i + 4
        bg = xl_row_bg(i)
        xl_cell(ws, r, 1, cl.get("nombre",    ""),  fg=bg, bold=True)
        xl_cell(ws, r, 2, cl.get("apellido",  ""),  fg=bg, bold=True)
        xl_cell(ws, r, 3, cl.get("telefono",  "—"), fg=bg)
        xl_cell(ws, r, 4, cl.get("correo",    "—"), fg=bg)
        xl_cell(ws, r, 5, cl.get("direccion", "—"), fg=bg)
        xl_badge_activo(ws, r, 6, cl.get("activo", 1))
        xl_cell(ws, r, 7, pedidos_map.get(cl["id_cliente"], 0), fg=bg, align="center")
        ws.row_dimensions[r].height = 16

    xl_col_widths(ws, [20, 20, 14, 28, 30, 11, 13])
    return wb


def exportar_cliente_excel_service(id_cliente, id_negocio=None, fecha_inicio=None, fecha_fin=None):
    """(Workbook, nombre_archivo) con los pedidos del cliente; None si el cliente no existe."""
    cliente, pedidos, detalles_map, pagos_map = exportar_cliente_service(
        id_cliente, id_negocio, fecha_inicio, fecha_fin
    )
    if not cliente:
        return None

    nombre_cliente = f"{cliente['nombre']} {cliente['apellido']}"
    filtro_txt = "  ".join(filter(None, [
        f"Desde: {fecha_inicio}" if fecha_inicio else "",
        f"Hasta: {fecha_fin}"   if fecha_fin    else "",
    ])) or "Sin filtros de fecha"

    wb = build_excel_cliente(pedidos, detalles_map, pagos_map, nombre_cliente, filtro_txt)
    nombre_archivo = f"pedidos_{cliente['nombre']}_{cliente['apellido']}".replace(" ", "_")
    return wb, nombre_archivo
