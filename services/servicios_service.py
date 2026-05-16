from servicios import (
    contar_servicios,
    obtener_servicios,
    crear_servicio,
    actualizar_servicio,
    eliminar_servicio,
    obtener_historial_servicio,
    restaurar_servicio,
    existe_servicio_activo
)


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
        return "actualizado"
    crear_servicio(id_negocio, nombre, precio, id_usuario)
    return "creado"


def eliminar_servicio_service(id_servicio: int, id_usuario: int) -> bool:
    return eliminar_servicio(id_servicio, id_usuario)


def obtener_historial_servicio_service(id_servicio: int) -> list[dict]:
    return obtener_historial_servicio(id_servicio)


def restaurar_servicio_service(id_servicio: int, id_usuario: int) -> None:
    restaurar_servicio(id_servicio, id_usuario)
