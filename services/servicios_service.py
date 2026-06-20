import time

from models.negocio import obtener_negocios
from models.servicios import (
    contar_servicios,
    obtener_servicios,
    crear_servicio,
    actualizar_servicio,
    eliminar_servicio,
    obtener_historial_servicio,
    restaurar_servicio,
    existe_servicio_activo
)

_servicios_cache: dict = {}
_SERVICIOS_TTL = 300  # segundos


def listar_servicios(
    id_negocio: int | None = None,
    q: str = "",
    pagina: int = 1,
    por_pagina: int = 10,
    incluir_eliminados: bool = False,
) -> dict:
    offset = (pagina - 1) * por_pagina

    total = contar_servicios(
        id_negocio=id_negocio,
        q=q,
        incluir_eliminados=incluir_eliminados
    )

    total_paginas = (total + por_pagina - 1) // por_pagina

    servicios = obtener_servicios(
        id_negocio=id_negocio,
        q=q,
        incluir_eliminados=incluir_eliminados,
        limit=por_pagina,
        offset=offset
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


def obtener_historial_servicio_service(id_servicio: int) -> list[dict]:
    return obtener_historial_servicio(id_servicio)


def restaurar_servicio_service(id_servicio: int, id_usuario: int) -> None:
    restaurar_servicio(id_servicio, id_usuario)
    _invalidar_cache_servicios()


def exportar_servicios_service(id_negocio, incluir_eliminados):
    from config import MAX_FILAS_EXPORTAR
    return obtener_servicios(
        id_negocio=id_negocio,
        incluir_eliminados=incluir_eliminados,
        limit=MAX_FILAS_EXPORTAR,
        offset=0,
    )
