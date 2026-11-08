from datetime import date

from openpyxl import Workbook

from config import PAGO_LABEL, COMPROBANTE_LABEL
from utils import a_monto, calcular_paginacion, nombres_negocios
from services.excel_helpers import (
    xl_cell, xl_row_bg, xl_titulo_hoja, xl_fila_headers, xl_fila_totales,
    xl_col_widths, xl_badge_activo,
)
from models.negocio import obtener_negocios  # re-exported for routes
from models.gastos import (
    crear_gasto,
    actualizar_gasto,
    obtener_gastos,
    eliminar_gasto,
    contar_gastos,
    obtener_historial_gasto,
    restaurar_gasto,
    obtener_categorias,
    crear_categoria,
    actualizar_categoria,
    eliminar_categoria,
)


def listar_gastos(
    id_negocio: str | None = None,
    id_categoria: str | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    pagina: int = 1,
    por_pagina: int = 10,
    incluir_eliminados: bool = False,
    orden: str | None = None,
    direccion: str | None = None,
) -> dict:
    total = contar_gastos(
        id_negocio=id_negocio,
        id_categoria=id_categoria,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        incluir_eliminados=incluir_eliminados
    )
    offset, total_paginas = calcular_paginacion(total, pagina, por_pagina)

    gastos = obtener_gastos(
        id_negocio=id_negocio,
        id_categoria=id_categoria,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        limit=por_pagina,
        offset=offset,
        incluir_eliminados=incluir_eliminados,
        orden=orden,
        direccion=direccion,
    )

    return {
        "gastos":        gastos,
        "total":         total,
        "total_paginas": total_paginas,
    }


def _validar_gasto(datos: tuple) -> None:
    """datos = (id_negocio, id_categoria, descripcion, proveedor, total,
                fecha_registro, tipo_comprobante, tipo_pago, notas)"""
    _, _, descripcion, _, total, fecha_registro, tipo_comprobante, tipo_pago, _ = datos
    if not descripcion:
        raise ValueError("La descripción es obligatoria.")
    monto = a_monto(total)
    if monto is None or monto < 0:
        raise ValueError("El total del gasto no es válido.")
    try:
        date.fromisoformat(str(fecha_registro))
    except ValueError:
        raise ValueError("La fecha del gasto no es válida.")
    if tipo_comprobante not in COMPROBANTE_LABEL:
        raise ValueError("Tipo de comprobante no válido.")
    if tipo_pago not in PAGO_LABEL:
        raise ValueError("Método de pago no válido.")


def guardar_gasto_service(id_gasto: str | None, datos: tuple, id_usuario: int) -> str:
    _validar_gasto(datos)
    if id_gasto:
        actualizar_gasto(id_gasto, *datos, id_usuario)
        return "actualizado"
    else:
        crear_gasto(*datos, id_usuario)
        return "creado"


def eliminar_gasto_service(id_gasto: int, id_usuario: int) -> None:
    eliminar_gasto(id_gasto, id_usuario)


def restaurar_gasto_service(id_gasto: int, id_usuario: int) -> None:
    restaurar_gasto(id_gasto, id_usuario)


def crear_categoria_service(nombre: str) -> None:
    crear_categoria(nombre.strip())


def actualizar_categoria_service(id_categoria: int, nombre: str) -> None:
    actualizar_categoria(id_categoria, nombre.strip())


def eliminar_categoria_service(id_categoria: int) -> tuple[bool, str]:
    return eliminar_categoria(id_categoria)


def exportar_gastos_service(id_negocio, id_categoria, fecha_inicio, fecha_fin, incluir_eliminados):
    from config import MAX_FILAS_EXPORTAR
    return obtener_gastos(
        id_negocio, id_categoria, fecha_inicio, fecha_fin,
        limit=MAX_FILAS_EXPORTAR, offset=0,
        incluir_eliminados=incluir_eliminados,
    )


# ── Exportación a Excel ──────────────────────────────────────────────────────

def _nombres_categorias(ids):
    """Nombres de las categorías elegidas, para el subtítulo del Excel."""
    nombres = {c["id_categoria"]: c["nombre"] for c in obtener_categorias()}
    return ", ".join(nombres.get(i, str(i)) for i in ids)


def exportar_gastos_excel_service(id_negocio, id_categoria, fecha_inicio, fecha_fin,
                                  incluir_eliminados) -> Workbook:
    gastos = exportar_gastos_service(id_negocio, id_categoria, fecha_inicio, fecha_fin,
                                     incluir_eliminados)

    subtexto = "  ".join(filter(None, [
        f"Negocio: {nombres_negocios(id_negocio, obtener_negocios())}" if id_negocio else "",
        f"Categoría: {_nombres_categorias(id_categoria)}" if id_categoria else "",
        f"Desde: {fecha_inicio}" if fecha_inicio else "",
        f"Hasta: {fecha_fin}"    if fecha_fin    else "",
    ])) or "Sin filtros — todos los registros"

    ncols   = 11
    headers = ["Negocio", "Descripción", "Categoría", "Notas",
               "Proveedor", "Total ($)", "Comprobante", "Método de pago",
               "Fecha registro", "Registrado por", "Estado"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Gastos"
    ws.freeze_panes = "A4"

    xl_titulo_hoja(ws, "Gastos — Fresh Steps", ncols, subtexto)
    xl_fila_headers(ws, headers)

    for i, g in enumerate(gastos):
        r  = i + 4
        bg = xl_row_bg(i)
        comprobante = g.get("tipo_comprobante", "")
        metodo      = g.get("tipo_pago", "")
        fr          = g.get("fecha_registro")
        xl_cell(ws, r,  1, g.get("negocio",     ""),   fg=bg)
        xl_cell(ws, r,  2, g.get("descripcion", ""),   fg=bg)
        xl_cell(ws, r,  3, g.get("categoria") or "—",  fg=bg)
        xl_cell(ws, r,  4, g.get("notas") or "",       fg=bg)
        xl_cell(ws, r,  5, g.get("proveedor",   ""),   fg=bg)
        xl_cell(ws, r,  6, float(g.get("total") or 0), fg=bg, bold=True, align="right",
                num_fmt='"$"#,##0.00')
        xl_cell(ws, r,  7, COMPROBANTE_LABEL.get(comprobante, comprobante), fg=bg)
        xl_cell(ws, r,  8, PAGO_LABEL.get(metodo, metodo), fg=bg)
        xl_cell(ws, r,  9, fr.strftime("%d/%m/%Y") if fr else "—", fg=bg)
        xl_cell(ws, r, 10, g.get("creado_por", "—"), fg=bg)
        xl_badge_activo(ws, r, 11, g.get("activo", 1))
        ws.row_dimensions[r].height = 16

    if gastos:
        xl_fila_totales(ws, len(gastos) + 4, ncols, [6])

    xl_col_widths(ws, [18, 28, 20, 30, 22, 13, 13, 18, 16, 18, 11])
    return wb
