from utils import calcular_paginacion
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
        incluir_eliminados=incluir_eliminados
    )

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
