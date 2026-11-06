import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from config import METODOS_PAGO_VALIDOS, POR_PAGINA_VENTAS_ACTIVAS
from utils import a_entero, a_monto, calcular_paginacion
from models.ventas import (
    eliminar_venta,
    marcar_entregada,
    registrar_pago_final_y_entregar,
    marcar_como_lista,
    revertir_lista,
    obtener_venta,
    obtener_ventas_listas,
    obtener_detalles_venta,
    obtener_entregas_pendientes,
    obtener_historial_ventas,
    obtener_historial_venta,
    contar_historial_ventas,
    contar_entregas_listas,
    contar_entregas_pendientes,
    contar_articulos_entregas,
    crear_venta,
)

from models.pagos import (
    obtener_pagos_venta,
)

from models.negocio import obtener_negocios, cargar_tipos_por_negocio
from models.clientes import cliente_activo
from models.servicios import ids_servicios_activos

logger = logging.getLogger(__name__)


def semanas_desde(fecha, hoy: date | None = None) -> int:
    """Semanas completas transcurridas desde `fecha` (0 si no hay fecha o es futura)."""
    if not fecha:
        return 0
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    return max((hoy or date.today()) - fecha, timedelta(0)).days // 7


def _paginar_ventas(
    contar_fn,
    obtener_fn,
    id_negocio: int | None,
    id_venta: str | None,
    pagina: int,
    q: str | None = None,
    orden: str | None = None,
    direccion: str | None = None,
    articulo: str | None = None,
) -> tuple[list, int, int]:
    total_registros          = contar_fn(id_negocio, id_venta, q, articulo=articulo)
    offset, total_paginas    = calcular_paginacion(total_registros, pagina, POR_PAGINA_VENTAS_ACTIVAS)
    ventas = obtener_fn(
        id_negocio, id_venta=id_venta, q=q,
        limit=POR_PAGINA_VENTAS_ACTIVAS, offset=offset,
        orden=orden, direccion=direccion, articulo=articulo,
    )
    return ventas, total_registros, total_paginas


def _enriquecer_ventas(
    ventas: list,
    *,
    con_pagos: bool = False,
    calcular_estado: bool = False,
) -> None:
    """Mutates ventas in-place: attaches detalles, optionally pagos/totals/estado."""
    if not ventas:
        return
    ids_venta    = [v["id_venta"] for v in ventas]
    detalles_map = obtener_detalles_venta(ids_venta)
    pagos_map    = obtener_pagos_venta(ids_venta) if (con_pagos or calcular_estado) else {}

    for v in ventas:
        v["detalles"] = detalles_map.get(v["id_venta"], [])

        if con_pagos:
            pagos        = pagos_map.get(v["id_venta"], [])
            total        = Decimal(str(v.get("total") or 0))
            total_pagado = sum(Decimal(str(p["monto"])) for p in pagos)
            v["pagos"]           = pagos
            v["total"]           = total
            v["total_pagado"]    = total_pagado
            v["saldo_pendiente"] = max(total - total_pagado, Decimal(0))
            v["tiene_pagos"]     = total_pagado > 0
            v["esta_pagada"]     = v["saldo_pendiente"] == 0

        if calcular_estado:
            pagos        = pagos_map.get(v["id_venta"], [])
            total        = Decimal(str(v.get("total") or 0))
            total_pagado = Decimal(str(v.get("total_pagado") or 0))
            v["pagos"]           = pagos
            v["total"]           = total
            v["total_pagado"]    = total_pagado
            v["saldo_pendiente"] = max(total - total_pagado, Decimal(0))
            v["esta_pagada"]     = v["saldo_pendiente"] == 0

            if v.get("eliminado"):
                v["estado"] = "eliminada"
            elif v.get("fecha_entrega"):
                v["estado"] = "entregada"
            elif v.get("fecha_lista"):
                v["estado"] = "lista"
            else:
                v["estado"] = "pendiente"


def listar_ventas_listas_service(
    id_negocio: int | None = None,
    pagina: int = 1,
    id_venta: str | None = None,
    q: str | None = None,
    orden: str | None = None,
    direccion: str | None = None,
    articulo: str | None = None,
) -> dict:
    ventas, total_registros, total_paginas = _paginar_ventas(
        contar_entregas_listas, obtener_ventas_listas,
        id_negocio, id_venta, pagina, q=q,
        orden=orden, direccion=direccion, articulo=articulo,
    )
    _enriquecer_ventas(ventas, con_pagos=True)
    hoy = date.today()
    for v in ventas:
        v["semanas_lista"] = semanas_desde(v.get("fecha_lista"), hoy)
    return {
        "ventas":          ventas,
        "negocios":        obtener_negocios(),
        "hoy":             hoy,
        "id_negocio":      id_negocio,
        "id_venta":        id_venta,
        "q":               q,
        "articulo":        articulo,
        "pagina":          pagina,
        "total_paginas":   total_paginas,
        "total_registros": total_registros,
        "total_articulos": contar_articulos_entregas(True, id_negocio, id_venta, q, articulo),
        "orden":           orden,
        "direccion":       direccion,
    }


def listar_entregas_pendientes_service(
    id_negocio: int | None = None,
    pagina: int = 1,
    id_venta: str | None = None,
    q: str | None = None,
    orden: str | None = None,
    direccion: str | None = None,
    articulo: str | None = None,
) -> dict:
    ventas, total_registros, total_paginas = _paginar_ventas(
        contar_entregas_pendientes, obtener_entregas_pendientes,
        id_negocio, id_venta, pagina, q=q,
        orden=orden, direccion=direccion, articulo=articulo,
    )
    _enriquecer_ventas(ventas)
    return {
        "ventas":          ventas,
        "negocios":        obtener_negocios(),
        "hoy":             date.today(),
        "id_negocio":      id_negocio,
        "id_venta":        id_venta,
        "q":               q,
        "articulo":        articulo,
        "pagina":          pagina,
        "total_paginas":   total_paginas,
        "total_registros": total_registros,
        "total_articulos": contar_articulos_entregas(False, id_negocio, id_venta, q, articulo),
        "orden":           orden,
        "direccion":       direccion,
    }


def registrar_pago_final_service(data: dict, id_usuario: int) -> tuple[bool, str]:
    """Cobra el saldo pendiente de una venta lista y la marca como entregada.

    Toda la validación de estado y saldo ocurre dentro de una sola transacción
    en `registrar_pago_final_y_entregar`."""
    id_venta    = a_entero(data.get("id_venta"))
    monto_raw   = data.get("monto")
    metodo_pago = data.get("metodo_pago")

    if not id_venta or monto_raw in (None, "") or not metodo_pago:
        return False, "Datos incompletos para el pago final"

    if metodo_pago not in METODOS_PAGO_VALIDOS:
        return False, f"Método de pago no válido: '{metodo_pago}'"

    monto = a_monto(monto_raw)
    if monto is None:
        return False, "El monto no es válido."
    if monto <= 0:
        return False, "El monto debe ser mayor a 0."

    try:
        registrar_pago_final_y_entregar(id_venta, monto, metodo_pago, id_usuario)
    except ValueError as e:
        return False, str(e)

    return True, "Pago final registrado y venta marcada como entregada"


def eliminar_venta_service(id_venta: int, id_usuario: int | None = None) -> None:
    venta = obtener_venta(id_venta)
    if not venta:
        raise ValueError("La venta no existe")
    eliminar_venta(id_venta, id_usuario)


def _parsear_prepago(form: dict) -> tuple[bool, Decimal]:
    if form.get("prepago") != "si":
        return False, Decimal(0)
    raw = form.get("monto_prepago")
    monto = a_monto(raw) if raw not in (None, "") else Decimal(0)
    if monto is None or monto < 0:
        raise ValueError("El monto del prepago no es válido.")
    return True, monto


def _parsear_descuento(form: dict) -> tuple[bool, Decimal]:
    if form.get("aplica_descuento") != "si":
        return False, Decimal(0)
    raw = form.get("cantidad_descuento")
    monto = a_monto(raw) if raw not in (None, "") else Decimal(0)
    if monto is None or monto < 0:
        raise ValueError("El monto del descuento no es válido.")
    return True, monto


def _cantidad(valor) -> int:
    """Cantidad de piezas: entero >= 1 (vacío = 1)."""
    if valor in (None, ""):
        return 1
    n = a_entero(str(valor).strip())
    if n is None:
        raise ValueError("La cantidad debe ser un número entero mayor a 0.")
    return n


def _precio_unitario(valor) -> Decimal:
    monto = a_monto(valor)
    if monto is None or monto <= 0:
        raise ValueError("El precio unitario debe ser mayor a 0.")
    return monto


def _texto(valor) -> str | None:
    return valor.strip() if isinstance(valor, str) else valor


def _parsear_fecha_estimada(valor) -> str | None:
    """Fecha estimada en formato ISO ('2026-11-06 14:30' o '2026-11-06T14:30'); None si viene vacía."""
    if not valor or not str(valor).strip():
        return None
    try:
        return datetime.fromisoformat(str(valor).strip()).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise ValueError("La fecha estimada no es válida.")


def validar_servicios_negocio(articulos: list, id_negocio: int) -> None:
    """Todos los servicios de los artículos deben existir, estar activos y ser del negocio."""
    ids = {s["id_servicio"] for a in articulos for s in (a.get("servicios") or [])}
    if not ids:
        return
    if ids - ids_servicios_activos(ids, id_negocio):
        raise ValueError("Uno de los servicios no existe, está eliminado o no pertenece a este negocio.")



_CAMPOS_ARTICULO: dict[str, dict[str, object]] = {
    "calzado": {
        "tipo":             _texto,
        "marca":            _texto,
        "material":         _texto,
        "color_base":       _texto,
        "color_secundario": _texto,
        "color_agujetas":   _texto,
    },
    "confeccion": {
        "tipo":             _texto,
        "marca":            _texto,
        "material":         _texto,
        "color_base":       _texto,
        "color_secundario": _texto,
        "cantidad":         _cantidad,
    },
    "maquila": {
        "tipo":            _texto,
        "cantidad":        _cantidad,
        "precio_unitario": _precio_unitario,
    },
}

# Tipos que requieren la sección de servicios
_TIPOS_CON_SERVICIOS: frozenset[str] = frozenset({"calzado", "confeccion"})


def _parsear_articulo_unico(form: dict, i: int, tipo_articulo: str) -> dict:
    schema = _CAMPOS_ARTICULO.get(tipo_articulo)
    if not schema:
        raise ValueError(f"Tipo de artículo desconocido: '{tipo_articulo}'")

    datos = {
        campo: converter(form.get(f"articulos[{i}][{campo}]"))
        for campo, converter in schema.items()
    }

    articulo: dict = {
        "tipo_articulo": tipo_articulo,
        "datos":         datos,
        "comentario":    form.get(f"articulos[{i}][comentario]"),
    }

    if tipo_articulo in _TIPOS_CON_SERVICIOS:
        articulo["servicios"] = _parsear_servicios(form, i)

    return articulo


def _parsear_articulos_form(form: dict, tipo_permitido: str | None) -> list:
    articulos: list = []
    try:
        i = 0
        while True:
            tipo_articulo = form.get(f"articulos[{i}][tipo_articulo]")
            if not tipo_articulo:
                break
            if tipo_permitido and tipo_articulo != tipo_permitido:
                raise ValueError(
                    f"Este negocio solo permite artículos tipo: {tipo_permitido}"
                )
            articulos.append(_parsear_articulo_unico(form, i, tipo_articulo))
            i += 1
    except ValueError:
        raise
    except TypeError:  # pragma: no cover
        raise ValueError("Datos de artículos inválidos (cantidad o precio no numérico).")
    return articulos


def _validar_reglas_negocio(tipo_negocio: str | None, articulos: list) -> None:
    if tipo_negocio in ("calzado", "confeccion"):
        for a in articulos:
            if not a.get("servicios"):
                raise ValueError("Cada artículo debe tener al menos 1 servicio.")
            for s in a["servicios"]:
                if not s.get("id_servicio"):
                    raise ValueError("Servicio inválido (sin id).")
                if Decimal(str(s.get("precio_aplicado") or 0)) <= 0:
                    raise ValueError("El precio aplicado debe ser mayor a 0.")
    if tipo_negocio == "maquila":
        for a in articulos:
            if a.get("servicios"):
                raise ValueError("Maquila no permite servicios.")


def guardar_venta_service(form: dict, id_usuario_creo: int) -> tuple[int | None, str | None]:
    try:
        try:
            id_negocio = int(form["id_negocio"])
        except (KeyError, ValueError):
            return None, "Negocio inválido."

        id_cliente     = a_entero(form.get("id_cliente") or "")
        fecha_estimada = _parsear_fecha_estimada(form.get("fecha_estimada"))

        prepago, monto_prepago   = _parsear_prepago(form)
        aplica_descuento, cantidad_descuento = _parsear_descuento(form)
        tipo_negocio = cargar_tipos_por_negocio().get(id_negocio)
        articulos = _parsear_articulos_form(form, tipo_negocio)

        if not id_cliente or not fecha_estimada:
            return None, "Faltan datos obligatorios (cliente, negocio, fecha estimada o tipo de pago)."

        if not articulos:
            return None, "Debes agregar al menos 1 artículo."

        _validar_reglas_negocio(tipo_negocio, articulos)
        validar_servicios_negocio(articulos, id_negocio)

        if not cliente_activo(id_cliente):
            return None, "El cliente seleccionado no existe o está eliminado."

        datos_prepago = None
        if prepago and monto_prepago > 0:
            tipo_pago = form.get("tipo_pago")
            if not tipo_pago:
                return None, "Debes seleccionar el tipo de pago del prepago."
            if tipo_pago not in METODOS_PAGO_VALIDOS:
                return None, f"Método de pago no válido: '{tipo_pago}'"
            datos_prepago = {"monto": monto_prepago, "tipo_pago": tipo_pago}

        # Venta, artículos y prepago en una sola transacción: si algo falla no queda nada guardado.
        id_venta = crear_venta(
            id_negocio=id_negocio,
            id_cliente=id_cliente,
            fecha_estimada=fecha_estimada,
            aplica_descuento=aplica_descuento,
            cantidad_descuento=cantidad_descuento,
            articulos=articulos,
            id_usuario_creo=id_usuario_creo,
            prepago=datos_prepago,
        )

        return id_venta, None

    except ValueError as e:
        return None, str(e)
    except Exception:  # pragma: no cover
        logger.exception("Error inesperado en guardar_venta_service")
        return None, "Error interno del servidor."


def _parsear_servicios(form: dict, i: int) -> list[dict]:
    servicios = []
    j = 0
    while True:
        id_serv = form.get(f"articulos[{i}][servicios][{j}][id_servicio]")
        if not id_serv:
            break
        id_servicio = a_entero(str(id_serv).strip())
        precio_raw  = form.get(f"articulos[{i}][servicios][{j}][precio_aplicado]")
        precio_ap   = a_monto(precio_raw) if precio_raw not in (None, "") else Decimal(0)
        if id_servicio is None or precio_ap is None:
            raise ValueError("Servicio o precio inválido.")
        servicios.append({"id_servicio": id_servicio, "precio_aplicado": precio_ap})
        j += 1
    return servicios


from config import POR_PAGINA_HISTORIAL_VENTAS as POR_PAGINA_HISTORIAL


def historial_ventas_service(
    id_negocio: int | list[int] | None = None,
    fecha_inicio: str | None = None,
    fecha_fin: str | None = None,
    pagina: int = 1,
    mostrar_eliminadas: bool = False,
    q: str | None = None,
    id_venta: int | None = None,
    estado: str | list[str] | None = None,
    tipo_fecha: str = "fecha_recibo",
    orden: str | None = None,
    direccion: str | None = None,
    articulo: str | None = None,
) -> dict:
    total_registros       = contar_historial_ventas(
        id_negocio, fecha_inicio, fecha_fin, mostrar_eliminadas,
        q=q, id_venta=id_venta, estado=estado, tipo_fecha=tipo_fecha,
        articulo=articulo,
    )
    offset, total_paginas = calcular_paginacion(total_registros, pagina, POR_PAGINA_HISTORIAL)

    ventas   = obtener_historial_ventas(
        id_negocio, fecha_inicio, fecha_fin,
        limit=POR_PAGINA_HISTORIAL, offset=offset,
        mostrar_eliminadas=mostrar_eliminadas, q=q, id_venta=id_venta,
        estado=estado, tipo_fecha=tipo_fecha,
        orden=orden, direccion=direccion, articulo=articulo,
    )
    negocios = obtener_negocios()

    _enriquecer_ventas(ventas, calcular_estado=True)

    return {
        "ventas":             ventas,
        "negocios":           negocios,
        "hoy":                date.today(),
        "id_negocio":         id_negocio,
        "fecha_inicio":       fecha_inicio,
        "fecha_fin":          fecha_fin,
        "pagina":             pagina,
        "total_paginas":      total_paginas,
        "total_registros":    total_registros,
        "mostrar_eliminadas": mostrar_eliminadas,
        "q":                  q,
        "articulo":           articulo,
        "id_venta":           id_venta,
        "estado":             estado,
        "tipo_fecha":         tipo_fecha,
        "orden":              orden,
        "direccion":          direccion,
    }


def marcar_lista_service(id_venta: int, id_usuario: int | None = None) -> bool:
    return marcar_como_lista(id_venta, id_usuario)


def revertir_lista_service(id_venta: int, id_usuario: int | None = None) -> bool:
    return revertir_lista(id_venta, id_usuario)

