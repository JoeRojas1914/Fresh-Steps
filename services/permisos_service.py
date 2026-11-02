"""Negocios que puede ver el usuario en sesión.

Los admin ven todos los negocios. Los usuarios de caja solo ven los negocios
que el admin les asignó (tabla usuario_negocio). Se consulta en cada request
(con caché en `g`) para que un cambio del admin aplique sin volver a iniciar sesión.
"""
from flask import g, session

from models.usuario import obtener_negocios_usuario
from models.negocio import obtener_negocios
from models.ventas import obtener_venta
from models.clientes import cliente_visible

# Ningún negocio tiene id 0: filtrar por [0] no devuelve nada.
SIN_NEGOCIOS = [0]


def negocios_permitidos() -> list[int] | None:
    """None = sin restricción (admin). Lista = IDs permitidos (caja)."""
    if session.get("rol") == "admin":
        return None
    if "negocios_permitidos" not in g:
        id_usuario = session.get("id_usuario")
        g.negocios_permitidos = obtener_negocios_usuario(id_usuario) if id_usuario else []
    return g.negocios_permitidos


def restringir_negocios(solicitados=None):
    """Recorta el filtro de negocio pedido a lo que el usuario puede ver.

    - Admin: regresa lo solicitado sin cambios.
    - Caja: la intersección con sus negocios; si no pidió nada (o pidió
      algo que no tiene), todos sus negocios. Sin negocios asignados no ve nada.
    """
    permitidos = negocios_permitidos()
    if permitidos is None:
        return solicitados
    if not permitidos:
        return SIN_NEGOCIOS

    if solicitados is None or solicitados == "":
        pedidos = []
    elif isinstance(solicitados, (list, tuple, set)):
        pedidos = list(solicitados)
    else:
        pedidos = [solicitados]
    pedidos = [int(n) for n in pedidos if str(n).isdigit()]

    interseccion = [n for n in pedidos if n in permitidos]
    return interseccion or list(permitidos)


def puede_usar_negocio(id_negocio) -> bool:
    permitidos = negocios_permitidos()
    if permitidos is None:
        return True
    try:
        return int(id_negocio) in permitidos
    except (TypeError, ValueError):
        return False


def puede_ver_venta(id_venta: int, estricto: bool = False) -> bool:
    """False si la venta existe y pertenece a un negocio no permitido.

    Si la venta no existe (o está eliminada) regresa True para que la ruta
    responda como siempre (404 / "no existe"). Con `estricto=True` regresa False:
    la caja no puede consultar ventas eliminadas."""
    permitidos = negocios_permitidos()
    if permitidos is None:
        return True
    venta = obtener_venta(id_venta)
    if not venta:
        return not estricto
    return venta["id_negocio"] in permitidos


def puede_ver_cliente(id_cliente: int) -> bool:
    """La caja solo ve clientes activos con alguna venta en sus negocios."""
    permitidos = negocios_permitidos()
    if permitidos is None:
        return True
    return cliente_visible(id_cliente, restringir_negocios())


def negocios_visibles() -> list[dict]:
    """Negocios (id_negocio, nombre, ...) que el usuario puede ver."""
    negocios   = obtener_negocios()
    permitidos = negocios_permitidos()
    if permitidos is None:
        return negocios
    return [n for n in negocios if n["id_negocio"] in permitidos]
