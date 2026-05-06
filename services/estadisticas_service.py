from datetime import date, datetime, timedelta
from clientes import contar_clientes
from servicios import contar_servicios
from negocio import obtener_negocios

from estadisticas import (
    contar_ventas_por_semana,
    obtener_gastos_por_semana_y_proveedor,
    obtener_total_gastos,
    obtener_total_ingresos,
    obtener_unidades_por_semana,
    obtener_ingresos_por_semana,
    obtener_ventas_con_y_sin_prepago,
    obtener_uso_servicios,
    obtener_ventas_por_dia,
    obtener_ticket_promedio,
    obtener_saldo_por_cobrar,
)

MAX_DIAS_RANGO = 186  


def dashboard_page_data_service():
    hoy          = date.today()
    fecha_inicio = hoy.replace(day=1)
    fecha_fin    = hoy
    return {
        "total_clientes":  contar_clientes(),
        "total_servicios": contar_servicios(),
        "negocios":        obtener_negocios(),
        "fecha_inicio":    fecha_inicio.isoformat(),
        "fecha_fin":       fecha_fin.isoformat(),
    }


def _periodo_anterior(inicio: date, fin: date):
    """Devuelve (inicio, fin) del período inmediatamente anterior de igual duración."""
    duracion   = (fin - inicio).days + 1
    fin_ant    = inicio - timedelta(days=1)
    inicio_ant = fin_ant - timedelta(days=duracion - 1)
    return inicio_ant, fin_ant


def dashboard_api_service(args):
    inicio_str = args.get("inicio")
    fin_str    = args.get("fin")
    id_negocio = args.get("id_negocio", "all")

    if not inicio_str or not fin_str:
        return None, "Faltan fechas"

    try:
        inicio = datetime.strptime(inicio_str, "%Y-%m-%d").date()
        fin    = datetime.strptime(fin_str,    "%Y-%m-%d").date()
    except ValueError:
        return None, "Formato de fecha inválido (usa YYYY-MM-DD)"

    if fin < inicio:
        return None, "La fecha fin no puede ser menor a inicio"

    if (fin - inicio).days > MAX_DIAS_RANGO:
        return None, f"El rango máximo permitido es {MAX_DIAS_RANGO} días (~6 meses)"

    total_ingresos              = obtener_total_ingresos(inicio, fin, id_negocio)
    total_gastos                = obtener_total_gastos(inicio,   fin, id_negocio)
    ticket_promedio, num_ventas = obtener_ticket_promedio(inicio, fin, id_negocio)
    saldo_por_cobrar            = obtener_saldo_por_cobrar(inicio, fin, id_negocio)
    total_ventas                = num_ventas  

    inicio_ant, fin_ant              = _periodo_anterior(inicio, fin)
    ingresos_ant                     = obtener_total_ingresos(inicio_ant, fin_ant, id_negocio)
    gastos_ant                       = obtener_total_gastos(inicio_ant,   fin_ant, id_negocio)
    ticket_ant, ventas_ant           = obtener_ticket_promedio(inicio_ant, fin_ant, id_negocio)
    saldo_ant                        = obtener_saldo_por_cobrar(inicio_ant, fin_ant, id_negocio)

    def pct_cambio(actual, anterior):
        """Devuelve % de cambio redondeado a 1 decimal, o None si no hay base."""
        if anterior == 0:
            return None
        return round((actual - anterior) / anterior * 100, 1)

    ganancia     = total_ingresos - total_gastos
    ganancia_ant = ingresos_ant   - gastos_ant

    ventas_semanales   = contar_ventas_por_semana(inicio, fin, id_negocio)
    gastos_semanales   = obtener_gastos_por_semana_y_proveedor(inicio, fin, id_negocio)
    ingresos_semanales = obtener_ingresos_por_semana(inicio, fin, id_negocio)
    unidades_semanales = obtener_unidades_por_semana(inicio, fin, id_negocio)

    ventas_prepago = obtener_ventas_con_y_sin_prepago(inicio, fin, id_negocio)
    uso_servicios  = obtener_uso_servicios(inicio, fin, id_negocio)
    ventas_por_dia = obtener_ventas_por_dia(inicio, fin, id_negocio)

    return {
        "ventas_semanales":   ventas_semanales,
        "gastos_semanales":   gastos_semanales,
        "ingresos_semanales": ingresos_semanales,
        "unidades_semanales": unidades_semanales,
        "ventas_prepago":     ventas_prepago,
        "uso_servicios":      uso_servicios,
        "ventas_por_dia":     ventas_por_dia,
        "kpis": {
            "ingresos":         total_ingresos,
            "gastos":           total_gastos,
            "ganancia":         ganancia,
            "ticket_promedio":  ticket_promedio,
            "num_ventas":       num_ventas,
            "total_ventas":     num_ventas,
            "saldo_por_cobrar": saldo_por_cobrar,
            "ingresos_pct":     pct_cambio(total_ingresos,    ingresos_ant),
            "gastos_pct":       pct_cambio(total_gastos,      gastos_ant),
            "ganancia_pct":     pct_cambio(ganancia,          ganancia_ant),
            "ticket_pct":       pct_cambio(ticket_promedio,   ticket_ant),
            "ventas_pct":       pct_cambio(num_ventas,        ventas_ant),
            "saldo_pct":        pct_cambio(saldo_por_cobrar,  saldo_ant),
        }
    }, None