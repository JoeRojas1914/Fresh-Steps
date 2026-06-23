import re
from decimal import Decimal, InvalidOperation

from db import get_db
from models.ventas_editar import (
    obtener_venta_para_editar,
    obtener_articulos_con_servicios,
    editar_venta,
)
from models.negocio import cargar_tipos_por_negocio
from services.ventas_service import _parsear_articulos_form, _validar_reglas_negocio


def _validar_precios_edicion(ediciones_servicio: list) -> None:
    for edt in ediciones_servicio:
        precio = Decimal(str(edt.get("precio_aplicado") or 0))
        if precio <= 0:
            raise ValueError("El precio aplicado de un servicio debe ser mayor a $0.")


def _validar_post_eliminaciones(id_venta: int, tipo_negocio: str | None, eliminaciones: list) -> None:
    """Verifica que ningún artículo quede sin servicios tras las eliminaciones solicitadas."""
    if tipo_negocio not in ("calzado", "confeccion") or not eliminaciones:
        return

    ids_por_art: dict = {}
    for e in eliminaciones:
        ids_por_art.setdefault(e["id_articulo"], []).append(e["id_servicio"])

    with get_db() as (_, cursor):
        for id_art, ids_srv in ids_por_art.items():
            ph = ",".join(["%s"] * len(ids_srv))
            cursor.execute(
                f"SELECT COUNT(*) AS restantes"
                f" FROM articulo_servicio asv"
                f" JOIN articulo a ON a.id_articulo = asv.id_articulo"
                f" WHERE asv.id_articulo = %s"
                f"   AND a.id_venta = %s"
                f"   AND asv.id_servicio NOT IN ({ph})",
                [id_art, id_venta] + ids_srv,
            )
            if cursor.fetchone()["restantes"] == 0:
                cursor.execute(
                    "SELECT COUNT(*) + 1 AS pos FROM articulo"
                    " WHERE id_venta = %s AND id_articulo < %s",
                    (id_venta, id_art),
                )
                pos = cursor.fetchone()["pos"]
                raise ValueError(
                    f"El artículo #{pos} quedaría sin servicios. "
                    "Debe tener al menos 1 servicio activo."
                )


def obtener_venta_editar_service(id_venta: int) -> dict:
    venta = obtener_venta_para_editar(id_venta)
    if not venta:
        raise ValueError("Venta no encontrada o no está en estado pendiente.")
    articulos = obtener_articulos_con_servicios(id_venta)
    return {
        "venta":                venta,
        "articulos_existentes": articulos,
    }


def _parsear_dec(valor) -> Decimal:
    try:
        return Decimal(str(valor or "0"))
    except InvalidOperation:
        return Decimal("0")


def _parsear_servicios_nuevos(form) -> list:
    result: dict = {}
    for key, value in form.items():
        m = re.match(r"^existing_servicios\[(\d+)\]\[(\d+)\]\[(\w+)\]$", key)
        if not m:
            continue
        id_art = int(m.group(1))
        j      = int(m.group(2))
        campo  = m.group(3)
        result.setdefault(id_art, {}).setdefault(j, {})[campo] = value

    entries = []
    for id_art, filas in result.items():
        servicios = []
        for j in sorted(filas):
            fila   = filas[j]
            id_srv = fila.get("id_servicio")
            if not id_srv:
                continue
            servicios.append({
                "id_servicio":    int(id_srv),
                "precio_aplicado": _parsear_dec(fila.get("precio_aplicado")),
            })
        if servicios:
            entries.append({"id_articulo": id_art, "servicios": servicios})
    return entries


def _parsear_ediciones_servicio(form) -> list:
    result: dict = {}
    for key, value in form.items():
        m = re.match(r"^existing_edit\[(\d+)\]\[(\d+)\]\[(\w+)\]$", key)
        if not m:
            continue
        id_art = int(m.group(1))
        id_srv = int(m.group(2))
        campo  = m.group(3)
        result.setdefault(id_art, {}).setdefault(id_srv, {})[campo] = value

    entries = []
    for id_art, srvs in result.items():
        for id_srv, campos in srvs.items():
            entries.append({
                "id_articulo":    id_art,
                "id_servicio":    id_srv,
                "precio_aplicado": _parsear_dec(campos.get("precio_aplicado")),
            })
    return entries


def _parsear_ediciones_articulo(form) -> dict:
    result = {}
    for key, value in form.items():
        m = re.match(r"^art_edit\[(\d+)\]\[(\w+)\]$", key)
        if not m:
            continue
        result.setdefault(int(m.group(1)), {})[m.group(2)] = value.strip()
    return result


def _parsear_eliminaciones_servicio(form) -> list:
    entries = []
    for key, value in form.items():
        m = re.match(r"^existing_delete\[(\d+)\]\[(\d+)\]$", key)
        if not m or value != "1":
            continue
        entries.append({
            "id_articulo": int(m.group(1)),
            "id_servicio": int(m.group(2)),
        })
    return entries


def editar_venta_service(id_venta: int, form, id_usuario: int) -> dict:
    venta = obtener_venta_para_editar(id_venta)
    if not venta:
        raise ValueError("Venta no encontrada o no está en estado pendiente.")

    id_negocio   = venta["id_negocio"]
    tipo_negocio = cargar_tipos_por_negocio().get(id_negocio)

    fecha_fecha = (form.get("fecha_estimada_fecha") or "").strip()
    fecha_hora  = (form.get("fecha_estimada_hora") or "").strip()
    fecha_estimada = f"{fecha_fecha} {fecha_hora}:00" if (fecha_fecha and fecha_hora) else None

    nuevos_articulos = _parsear_articulos_form(form, tipo_negocio)
    if nuevos_articulos:
        _validar_reglas_negocio(tipo_negocio, nuevos_articulos)

    nuevos_servicios       = _parsear_servicios_nuevos(form)
    ediciones_servicio     = _parsear_ediciones_servicio(form)
    eliminaciones_servicio = _parsear_eliminaciones_servicio(form)
    ediciones_articulo     = _parsear_ediciones_articulo(form)

    sin_cambios = (
        not nuevos_articulos
        and not nuevos_servicios
        and not ediciones_servicio
        and not eliminaciones_servicio
        and not ediciones_articulo
        and not fecha_estimada
    )
    if sin_cambios:
        raise ValueError("No hay cambios para guardar.")

    _validar_precios_edicion(ediciones_servicio)
    _validar_post_eliminaciones(id_venta, tipo_negocio, eliminaciones_servicio)

    return editar_venta(
        id_venta=id_venta,
        fecha_estimada=fecha_estimada,
        nuevos_articulos=nuevos_articulos,
        nuevos_servicios_por_articulo=nuevos_servicios,
        ediciones_servicio=ediciones_servicio,
        eliminaciones_servicio=eliminaciones_servicio,
        ediciones_articulo=ediciones_articulo,
        id_usuario=id_usuario,
    )
