import time

from openpyxl import Workbook

from utils import a_monto, calcular_paginacion, nombres_negocios
from services.excel_helpers import (
    xl_cell, xl_row_bg, xl_titulo_hoja, xl_fila_headers, xl_col_widths, xl_badge_activo,
)

from models.negocio import obtener_negocios
from models.servicios import (
    contar_servicios,
    obtener_servicios,
    crear_servicio,
    actualizar_servicio,
    eliminar_servicio,
    obtener_historial_servicio,
    restaurar_servicio,
    existe_servicio_activo,
    alternar_servicio_default,
)

_servicios_cache: dict = {}
_SERVICIOS_TTL = 300  # segundos


def listar_servicios(
    id_negocio: int | None = None,
    q: str = "",
    pagina: int = 1,
    por_pagina: int = 10,
    incluir_eliminados: bool = False,
    orden: str | None = None,
    direccion: str | None = None,
) -> dict:
    total = contar_servicios(
        id_negocio=id_negocio,
        q=q,
        incluir_eliminados=incluir_eliminados
    )

    offset, total_paginas = calcular_paginacion(total, pagina, por_pagina)

    servicios = obtener_servicios(
        id_negocio=id_negocio,
        q=q,
        incluir_eliminados=incluir_eliminados,
        limit=por_pagina,
        offset=offset,
        orden=orden,
        direccion=direccion,
    )

    return {
        "servicios":     servicios,
        "total_paginas": total_paginas,
        "total":         total,
    }


def listar_servicios_api(id_negocio: int | None) -> dict:
    key = str(id_negocio)
    entry = _servicios_cache.get(key)
    if entry and (time.time() - entry[1]) < _SERVICIOS_TTL:
        return entry[0]
    # Solo se cachean negocios que existen: con ids arbitrarios la caché crecería sin límite
    if id_negocio is not None and id_negocio not in {n["id_negocio"] for n in obtener_negocios()}:
        return {"servicios": [], "total_paginas": 1, "total": 0}
    data = listar_servicios(id_negocio=id_negocio, pagina=1, por_pagina=1000)
    _servicios_cache[key] = (data, time.time())
    return data


def _invalidar_cache_servicios() -> None:
    _servicios_cache.clear()


def guardar_servicio_service(
    id_servicio: str | None,
    id_negocio: int,
    nombre: str,
    precio: float,
    id_usuario: int,
) -> str:
    if not nombre:
        raise ValueError("El nombre del servicio es obligatorio.")
    monto = a_monto(precio)
    if monto is None or monto < 0:
        raise ValueError("El precio del servicio no es válido.")
    if existe_servicio_activo(id_negocio, nombre, excluir_id=id_servicio or None):
        raise ValueError(f"Ya existe un servicio activo con el nombre '{nombre}' en este negocio.")
    if id_servicio:
        actualizar_servicio(id_servicio, id_negocio, nombre, precio, id_usuario)
    else:
        crear_servicio(id_negocio, nombre, precio, id_usuario)
    _invalidar_cache_servicios()
    return "actualizado" if id_servicio else "creado"


def eliminar_servicio_service(id_servicio: int, id_usuario: int) -> bool:
    result = eliminar_servicio(id_servicio, id_usuario)
    _invalidar_cache_servicios()
    return result


def alternar_servicio_default_service(id_servicio: int, id_usuario: int) -> bool:
    """Marca/quita el servicio como predeterminado de su negocio. True = quedó marcado."""
    resultado = alternar_servicio_default(id_servicio, id_usuario)
    if resultado is None:
        raise ValueError("El servicio no existe o está eliminado.")
    _invalidar_cache_servicios()
    return resultado


def obtener_historial_servicio_service(id_servicio: int) -> list[dict]:
    return obtener_historial_servicio(id_servicio)


def restaurar_servicio_service(id_servicio: int, id_usuario: int) -> None:
    restaurar_servicio(id_servicio, id_usuario)
    _invalidar_cache_servicios()


def exportar_servicios_service(id_negocio, incluir_eliminados, q=None, orden=None, direccion=None):
    from config import MAX_FILAS_EXPORTAR
    return obtener_servicios(
        id_negocio=id_negocio,
        q=q,
        incluir_eliminados=incluir_eliminados,
        limit=MAX_FILAS_EXPORTAR,
        offset=0,
        orden=orden,
        direccion=direccion,
    )


def exportar_servicios_excel_service(id_negocio, incluir_eliminados, q=None,
                                     orden=None, direccion=None) -> Workbook:
    servicios = exportar_servicios_service(id_negocio, incluir_eliminados, q=q,
                                           orden=orden, direccion=direccion)

    subtexto = nombres_negocios(id_negocio, obtener_negocios()) or "Todos los negocios"
    if q:
        subtexto += f"  |  Búsqueda: {q}"
    if incluir_eliminados:
        subtexto += "  |  Incluye eliminados"

    wb = Workbook()
    ws = wb.active
    ws.title = "Servicios"
    ws.freeze_panes = "A4"

    xl_titulo_hoja(ws, "Catálogo de Servicios — Fresh Steps", 4, subtexto)
    xl_fila_headers(ws, ["Negocio", "Servicio", "Precio ($)", "Estado"])

    for i, srv in enumerate(servicios):
        r  = i + 4
        bg = xl_row_bg(i)
        xl_cell(ws, r, 1, srv.get("negocio", ""), fg=bg)
        xl_cell(ws, r, 2, srv.get("nombre",  ""), fg=bg)
        xl_cell(ws, r, 3, float(srv.get("precio") or 0), fg=bg, bold=True,
                align="right", num_fmt='"$"#,##0.00')
        xl_badge_activo(ws, r, 4, srv.get("activo", 1))
        ws.row_dimensions[r].height = 16

    xl_col_widths(ws, [20, 32, 14, 12])
    return wb
