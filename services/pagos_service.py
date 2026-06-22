from utils import calcular_paginacion
from models.pagos import obtener_historial_pagos, contar_historial_pagos


def listar_pagos_service(id_negocio, tipo_pago, tipo_pago_venta,
                          fecha_inicio, fecha_fin, pagina, por_pagina=20):
    total = contar_historial_pagos(
        id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin
    )
    offset, total_paginas = calcular_paginacion(total, pagina, por_pagina)
    pagos = obtener_historial_pagos(
        id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin,
        limit=por_pagina, offset=offset,
    )
    return {"pagos": pagos, "total": total, "total_paginas": total_paginas}


def exportar_pagos_service(id_negocio, tipo_pago, tipo_pago_venta,
                            fecha_inicio, fecha_fin):
    return obtener_historial_pagos(
        id_negocio, tipo_pago, tipo_pago_venta, fecha_inicio, fecha_fin,
        limit=10_000, offset=0,
    )
