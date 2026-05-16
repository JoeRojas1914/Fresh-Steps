from gastos import (
    crear_gasto,
    actualizar_gasto,
    obtener_gastos,
    eliminar_gasto,
    contar_gastos,
    obtener_historial_gasto,
    restaurar_gasto
)


def listar_gastos(
    id_negocio: str | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    pagina: int = 1,
    por_pagina: int = 10,
    incluir_eliminados: bool = False,
) -> dict:
    offset = (pagina - 1) * por_pagina

    total = contar_gastos(
        id_negocio=id_negocio,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        incluir_eliminados=incluir_eliminados
    )

    gastos = obtener_gastos(
        id_negocio=id_negocio,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        limit=por_pagina,
        offset=offset,
        incluir_eliminados=incluir_eliminados
    )

    total_paginas = (total + por_pagina - 1) // por_pagina

    return {
        "gastos":        gastos,
        "total":         total,
        "total_paginas": total_paginas,
    }


def guardar_gasto_service(id_gasto: str | None, datos: tuple, id_usuario: int) -> str:
    if id_gasto:
        actualizar_gasto(id_gasto, *datos, id_usuario)
        return "actualizado"
    else:
        crear_gasto(*datos, id_usuario)
        return "creado"


def eliminar_gasto_service(id_gasto: int, id_usuario: int) -> None:
    eliminar_gasto(id_gasto, id_usuario)


def obtener_historial_gasto_service(id_gasto: int) -> list[dict]:
    return obtener_historial_gasto(id_gasto)


def restaurar_gasto_service(id_gasto: int, id_usuario: int) -> None:
    restaurar_gasto(id_gasto, id_usuario)
