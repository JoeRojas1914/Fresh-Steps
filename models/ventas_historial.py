from db import get_db
from models.ventas_detalles import filtro_articulo, filtro_cliente
from utils import (
    registrar_historial as _registrar_historial,
    construir_order_by,
    COLUMNAS_ORDEN_VENTAS,
)

COLUMNAS_ORDEN_HISTORIAL = {
    **COLUMNAS_ORDEN_VENTAS,
    "estado": "CASE WHEN v.eliminado = 1 THEN 3"
              " WHEN v.fecha_entrega IS NOT NULL THEN 2"
              " WHEN v.fecha_lista IS NOT NULL THEN 1 ELSE 0 END",
}

_COLS_FECHA_HISTORIAL = frozenset({"fecha_recibo", "fecha_lista", "fecha_entrega"})


def registrar_historial_venta(cursor, id_venta, accion, id_usuario, antes=None, despues=None):
    _registrar_historial(cursor, "venta_historial", "id_venta", id_venta, accion, id_usuario, antes, despues)


def obtener_historial_venta(id_venta):
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT h.id_historial, h.accion, h.datos_antes,
                   h.datos_despues, h.fecha, u.usuario
            FROM venta_historial h
            JOIN usuario u ON u.id_usuario = h.id_usuario
            WHERE h.id_venta = %s
            ORDER BY h.fecha ASC
        """, (id_venta,))
        return cursor.fetchall()


_CONDICIONES_ESTADO = {
    "pendiente": "(v.eliminado = 0 AND v.fecha_lista IS NULL AND v.fecha_entrega IS NULL)",
    "lista":     "(v.eliminado = 0 AND v.fecha_lista IS NOT NULL AND v.fecha_entrega IS NULL)",
    "entregada": "(v.eliminado = 0 AND v.fecha_entrega IS NOT NULL)",
    "eliminada": "(v.eliminado = 1)",
}


def _como_lista(valor):
    """Acepta None, un valor suelto o una lista y regresa una lista sin vacíos."""
    if valor is None:
        return []
    if not isinstance(valor, (list, tuple, set)):
        valor = [valor]
    return [v for v in valor if v not in (None, "")]


def _aplicar_filtro_estado(sql, params, estado, mostrar_eliminadas):
    condiciones = [_CONDICIONES_ESTADO[e] for e in _como_lista(estado) if e in _CONDICIONES_ESTADO]
    if condiciones:
        sql += " AND (" + " OR ".join(condiciones) + ")"
    elif not mostrar_eliminadas:
        sql += " AND v.eliminado = 0"
    return sql, params


def _aplicar_filtro_negocio(sql, params, id_negocio):
    ids = _como_lista(id_negocio)
    if ids:
        sql += f" AND v.id_negocio IN ({', '.join(['%s'] * len(ids))})"
        params.extend(ids)
    return sql, params


def contar_historial_ventas(
    id_negocio=None,
    fecha_inicio=None,
    fecha_fin=None,
    mostrar_eliminadas=False,
    q=None,
    id_venta=None,
    estado=None,
    tipo_fecha="fecha_recibo",
    articulo=None,
):
    col = tipo_fecha if tipo_fecha in _COLS_FECHA_HISTORIAL else "fecha_recibo"
    with get_db() as (_, cursor):
        sql = """
            SELECT COUNT(DISTINCT v.id_venta) AS total
            FROM venta v
            JOIN cliente c ON c.id_cliente = v.id_cliente
            WHERE 1=1
        """
        params = []
        sql, params = _aplicar_filtro_estado(sql, params, estado, mostrar_eliminadas)
        sql, params = _aplicar_filtro_negocio(sql, params, id_negocio)

        if fecha_inicio:
            sql += f" AND DATE(v.{col}) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += f" AND DATE(v.{col}) <= %s"
            params.append(fecha_fin)
        if q:
            sql_cli, params_cli = filtro_cliente(q)
            sql += sql_cli
            params.extend(params_cli)
        if articulo:
            sql_art, params_art = filtro_articulo(articulo)
            sql += sql_art
            params.extend(params_art)
        if id_venta:
            sql += " AND v.id_venta = %s"
            params.append(id_venta)

        cursor.execute(sql, params)
        return cursor.fetchone()["total"]


def obtener_historial_ventas(
    id_negocio=None,
    fecha_inicio=None,
    fecha_fin=None,
    limit=20,
    offset=0,
    mostrar_eliminadas=False,
    q=None,
    id_venta=None,
    estado=None,
    tipo_fecha="fecha_recibo",
    orden=None,
    direccion=None,
    articulo=None,
):
    col = tipo_fecha if tipo_fecha in _COLS_FECHA_HISTORIAL else "fecha_recibo"
    with get_db() as (_, cursor):
        sql = """
            SELECT
                v.id_venta,
                v.fecha_recibo,
                v.fecha_estimada,
                v.fecha_lista,
                v.fecha_entrega,
                v.eliminado,
                v.total,
                v.aplica_descuento,
                v.cantidad_descuento,
                c.nombre,
                c.apellido,
                c.telefono,
                n.nombre   AS negocio,
                n.id_negocio,
                u.usuario  AS usuario_creo,
                ue.usuario AS usuario_entrego,
                COALESCE(SUM(p.monto), 0) AS total_pagado
            FROM venta v
            JOIN cliente  c ON c.id_cliente  = v.id_cliente
            JOIN negocio  n ON n.id_negocio  = v.id_negocio
            LEFT JOIN usuario u  ON u.id_usuario  = v.id_usuario_creo
            LEFT JOIN usuario ue ON ue.id_usuario = v.id_usuario_entrego
            LEFT JOIN pago_venta p ON p.id_venta = v.id_venta
            WHERE 1=1
        """
        params = []
        sql, params = _aplicar_filtro_estado(sql, params, estado, mostrar_eliminadas)
        sql, params = _aplicar_filtro_negocio(sql, params, id_negocio)

        if fecha_inicio:
            sql += f" AND DATE(v.{col}) >= %s"
            params.append(fecha_inicio)
        if fecha_fin:
            sql += f" AND DATE(v.{col}) <= %s"
            params.append(fecha_fin)
        if q:
            sql_cli, params_cli = filtro_cliente(q)
            sql += sql_cli
            params.extend(params_cli)
        if articulo:
            sql_art, params_art = filtro_articulo(articulo)
            sql += sql_art
            params.extend(params_art)
        if id_venta:
            sql += " AND v.id_venta = %s"
            params.append(id_venta)

        sql += " GROUP BY v.id_venta"
        sql += construir_order_by(orden, direccion, "v.id_venta DESC", COLUMNAS_ORDEN_HISTORIAL)
        sql += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        return cursor.fetchall()
