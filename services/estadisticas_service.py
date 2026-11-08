import logging
import unicodedata
from datetime import date, datetime, timedelta
from models.clientes import contar_clientes
from models.ventas import contar_entregas_resumen
from models.estadisticas_ventas import (
    contar_unidades_por_dia_rango,
    contar_unidades_hoy,
    contar_ventas_entregadas_hoy,
)
from models.servicios import contar_servicios
from models.negocio import obtener_negocios

from models.estadisticas import (
    contar_ventas_por_semana,
    obtener_gastos_por_semana_y_proveedor,
    obtener_gastos_por_semana_y_categoria,
    obtener_total_gastos,
    obtener_total_ingresos,
    obtener_unidades_por_semana,
    obtener_ingresos_por_semana,
    obtener_ventas_con_y_sin_prepago,
    obtener_uso_servicios,
    obtener_ventas_por_dia,
    obtener_ticket_promedio,
    obtener_saldo_por_cobrar,
    obtener_top_clientes,
    obtener_tiempo_promedio_entrega,
    obtener_ingresos_por_negocio,
    obtener_metodos_pago,
    obtener_hora_pico_recepcion,
    obtener_hora_pico_entrega,
    obtener_clientes_unicos,
    obtener_clientes_nuevos,
    obtener_tasa_retorno,
    obtener_gasto_promedio_cliente,
    contar_ventas_por_hora,
    obtener_ingresos_por_hora,
    obtener_unidades_por_hora,
    contar_ventas_por_dia_rango,
    obtener_ingresos_por_dia_rango,
    obtener_unidades_por_dia_rango,
    obtener_top_calzado,
    obtener_primer_anio_ventas,
)

MAX_DIAS_RANGO = 186
MAX_DIAS_ANIO  = 366   # modo "Año" y exportación

_log = logging.getLogger(__name__)


def dashboard_page_data_service():
    hoy          = date.today()
    fecha_inicio = hoy.replace(day=1)
    fecha_fin    = hoy
    return {
        "total_clientes":  contar_clientes(),
        "total_servicios": contar_servicios(),
        "negocios":        obtener_negocios(),
        "anios":           list(range(hoy.year, min(obtener_primer_anio_ventas() or hoy.year, hoy.year) - 1, -1)),
        "fecha_inicio":    fecha_inicio.isoformat(),
        "fecha_fin":       fecha_fin.isoformat(),
    }


_MODOS = frozenset({"dia", "semana", "mes", "anio", "personalizado"})


def _periodo_anterior(inicio: date, fin: date):
    """Devuelve (inicio, fin) del período inmediatamente anterior de igual duración."""
    duracion   = (fin - inicio).days + 1
    fin_ant    = inicio - timedelta(days=1)
    inicio_ant = fin_ant - timedelta(days=duracion - 1)
    return inicio_ant, fin_ant


def _ultimo_dia_mes(d: date) -> date:
    siguiente = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return siguiente - timedelta(days=1)


def _mes_anterior(d: date) -> date:
    """Mismo número de día en el mes anterior (ajustado si ese mes es más corto)."""
    ultimo_ant = d.replace(day=1) - timedelta(days=1)
    return ultimo_ant.replace(day=min(d.day, ultimo_ant.day))


def _anio_anterior(d: date) -> date:
    """Misma fecha un año antes (el 29 de febrero pasa al 28)."""
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        return d.replace(year=d.year - 1, day=28)


def _periodo_comparacion(inicio: date, fin: date, modo: str | None, hoy: date | None = None):
    """
    Devuelve ((inicio_act, fin_act), (inicio_ant, fin_ant)) con el criterio "mismo avance":
    si el período aún no termina, se compara solo el tramo transcurrido contra el mismo
    tramo del período anterior (1–5 nov vs 1–5 oct).

    - mes:    mes calendario anterior, mismos días.
    - semana: semana anterior, mismos días de la semana.
    - dia:    mismo día de la semana anterior.
    - anio:   año anterior, mismas fechas (año completo si el actual ya terminó).
    - personalizado / None: período inmediato anterior de igual duración (comportamiento original).
    """
    if modo not in _MODOS or modo == "personalizado":
        return (inicio, fin), _periodo_anterior(inicio, fin)

    hoy   = hoy or date.today()
    corte = fin if hoy < inicio else min(fin, hoy)

    if modo == "mes":
        inicio_ant = _mes_anterior(inicio)
        if corte == fin and fin == _ultimo_dia_mes(fin):
            fin_ant = _ultimo_dia_mes(inicio_ant)   
        else:
            fin_ant = _mes_anterior(corte)
        return (inicio, corte), (inicio_ant, fin_ant)

    if modo == "anio":
        return (inicio, corte), (_anio_anterior(inicio), _anio_anterior(corte))

    semana = timedelta(days=7)
    return (inicio, corte), (inicio - semana, corte - semana)


def _pct_cambio(actual, anterior) -> float | None:
    if anterior is None or anterior <= 0:
        return None
    return round((actual - anterior) / anterior * 100, 1)


def _calcular_kpis(inicio: date, fin: date, id_negocio) -> dict:
    total_ingresos              = obtener_total_ingresos(inicio, fin, id_negocio)
    total_gastos                = obtener_total_gastos(inicio,   fin, id_negocio)
    ticket_promedio, num_ventas = obtener_ticket_promedio(inicio, fin, id_negocio)
    saldo_por_cobrar            = obtener_saldo_por_cobrar(inicio, fin, id_negocio)
    return {
        "ingresos":         total_ingresos,
        "gastos":           total_gastos,
        "ganancia":         total_ingresos - total_gastos,
        "ticket_promedio":  ticket_promedio,
        "num_ventas":       num_ventas,
        "total_ventas":     num_ventas,
        "saldo_por_cobrar": saldo_por_cobrar,
    }


def _calcular_comparativa(kpis: dict, inicio: date, fin: date, id_negocio,
                          modo: str | None = None) -> tuple[dict, dict, dict]:
    (inicio_act, fin_act), (inicio_ant, fin_ant) = _periodo_comparacion(inicio, fin, modo)
    ingresos_ant           = obtener_total_ingresos(inicio_ant, fin_ant, id_negocio)
    gastos_ant             = obtener_total_gastos(inicio_ant,   fin_ant, id_negocio)
    ticket_ant, ventas_ant = obtener_ticket_promedio(inicio_ant, fin_ant, id_negocio)
    ganancia_ant           = ingresos_ant - gastos_ant

    pcts = {
        "ingresos_pct": _pct_cambio(kpis["ingresos"],         ingresos_ant),
        "gastos_pct":   _pct_cambio(kpis["gastos"],           gastos_ant),
        "ganancia_pct": _pct_cambio(kpis["ganancia"],         ganancia_ant),
        "ticket_pct":   _pct_cambio(kpis["ticket_promedio"],  ticket_ant),
        "ventas_pct":   _pct_cambio(kpis["num_ventas"],       ventas_ant),
    }
    periodo_anterior_str = {"inicio": inicio_ant.isoformat(), "fin": fin_ant.isoformat()}
    periodo_actual_str   = {"inicio": inicio_act.isoformat(), "fin": fin_act.isoformat()}
    return pcts, periodo_anterior_str, periodo_actual_str



_SIN_NOMBRE = frozenset({"Sin marca", "Sin tipo"})


def _clave_nombre(nombre: str) -> str:
    """Forma comparable: sin acentos, en minúsculas y solo letras/números
    ("New-Balance", "new balance" y "NewBalance" → "newbalance")."""
    sin_acentos = unicodedata.normalize("NFKD", nombre)
    return "".join(c for c in sin_acentos.lower() if c.isalnum())


def _tolerancia(largo: int) -> int:
    """Errores de dedo permitidos según el largo. Los nombres cortos deben coincidir
    exacto: con 4 letras, un cambio ya puede ser otra marca ("Fila" / "Vila")."""
    if largo <= 4:
        return 0
    return 1 if largo <= 8 else 2


def _distancia(a: str, b: str, maximo: int) -> int:
    """Distancia de edición con transposiciones (Damerau-Levenshtein restringida):
    letra de más, de menos, cambiada o dos letras volteadas cuentan 1.
    Deja de calcular en cuanto se pasa de `maximo`."""
    if abs(len(a) - len(b)) > maximo:
        return maximo + 1
    previa2, previa = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        actual = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            costo = 0 if a[i - 1] == b[j - 1] else 1
            actual[j] = min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + costo)
            if (previa2 is not None and i > 1 and j > 1
                    and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]):
                actual[j] = min(actual[j], previa2[j - 2] + 1)
        if min(actual) > maximo:
            return maximo + 1
        previa2, previa = previa, actual
    return previa[-1]


def _nombre_visible(variantes: dict) -> str:
    """La forma más usada; si está toda en minúsculas o mayúsculas, con Mayúscula Inicial."""
    nombre = max(variantes.items(), key=lambda kv: kv[1])[0]
    return nombre.title() if nombre.islower() or nombre.isupper() else nombre


def agrupar_nombres_similares(filas: list[dict], limite: int = 8) -> list[dict]:
    """Une las variantes de un mismo nombre (mayúsculas, acentos, espacios y errores de
    dedo) y devuelve el top `limite` como [{"nombre", "total"}].

    Se recorren de más a menos frecuente: cada nombre se une al primer grupo cuya
    clave quede dentro de la tolerancia, así la forma correcta (la más común) manda.
    """
    grupos = []   # [{"clave", "total", "variantes": {nombre: total}}]
    for fila in sorted(filas, key=lambda f: -f["total"]):
        nombre = (fila["nombre"] or "").strip()
        clave  = _clave_nombre(nombre)
        exacto = nombre in _SIN_NOMBRE or not clave

        grupo = None
        for g in grupos:
            if g["exacto"] or exacto:
                coincide = g["clave"] == clave and g["exacto"] == exacto
            else:
                tol = _tolerancia(min(len(clave), len(g["clave"])))
                coincide = _distancia(clave, g["clave"], tol) <= tol
            if coincide:
                grupo = g
                break

        if grupo is None:
            grupo = {"clave": clave, "exacto": exacto, "total": 0, "variantes": {}}
            grupos.append(grupo)
        grupo["total"] += fila["total"]
        grupo["variantes"][nombre] = grupo["variantes"].get(nombre, 0) + fila["total"]

    grupos.sort(key=lambda g: -g["total"])
    return [{"nombre": _nombre_visible(g["variantes"]), "total": g["total"]} for g in grupos[:limite]]


def _cargar_series(inicio: date, fin: date, id_negocio, granularidad: str, agrupacion_gastos: str = "proveedor") -> dict:
    # Cubetas de las series largas y de los gastos: por mes en modo Año, si no por semana
    periodo = "mes" if granularidad == "mes" else "semana"
    if granularidad == "hora":
        ventas_semanales   = contar_ventas_por_hora(inicio, fin, id_negocio)
        ingresos_semanales = obtener_ingresos_por_hora(inicio, fin, id_negocio)
        unidades_semanales = obtener_unidades_por_hora(inicio, fin, id_negocio)
    elif granularidad == "dia":
        ventas_semanales   = contar_ventas_por_dia_rango(inicio, fin, id_negocio)
        ingresos_semanales = obtener_ingresos_por_dia_rango(inicio, fin, id_negocio)
        unidades_semanales = obtener_unidades_por_dia_rango(inicio, fin, id_negocio)
    else:
        ventas_semanales   = contar_ventas_por_semana(inicio, fin, id_negocio, periodo=periodo)
        ingresos_semanales = obtener_ingresos_por_semana(inicio, fin, id_negocio, periodo=periodo)
        unidades_semanales = obtener_unidades_por_semana(inicio, fin, id_negocio, periodo=periodo)

    if agrupacion_gastos == "categoria":
        gastos_semanales = obtener_gastos_por_semana_y_categoria(inicio, fin, id_negocio, periodo=periodo)
    else:
        gastos_semanales = obtener_gastos_por_semana_y_proveedor(inicio, fin, id_negocio, periodo=periodo)
    ventas_prepago     = obtener_ventas_con_y_sin_prepago(inicio, fin, id_negocio)
    uso_servicios      = obtener_uso_servicios(inicio, fin, id_negocio)
    ventas_por_dia     = obtener_ventas_por_dia(inicio, fin, id_negocio)
    top_clientes       = obtener_top_clientes(inicio, fin, id_negocio)
    tiempo_entrega     = obtener_tiempo_promedio_entrega(inicio, fin, id_negocio)
    ingresos_x_negocio = obtener_ingresos_por_negocio(inicio, fin) if id_negocio == "all" else []
    metodos_pago       = obtener_metodos_pago(inicio, fin, id_negocio)
    hora_recepcion     = obtener_hora_pico_recepcion(inicio, fin, id_negocio)
    hora_entrega       = obtener_hora_pico_entrega(inicio, fin, id_negocio)
    clientes_unicos    = obtener_clientes_unicos(inicio, fin, id_negocio)
    hay_calzado        = str(id_negocio) in ("all", "1")
    calzado_marcas     = agrupar_nombres_similares(obtener_top_calzado(inicio, fin, "marca")) if hay_calzado else []
    calzado_tipos      = agrupar_nombres_similares(obtener_top_calzado(inicio, fin, "tipo"))  if hay_calzado else []

    try:
        clientes_nuevos = obtener_clientes_nuevos(inicio, fin, id_negocio)
    except Exception as e:  # pragma: no cover
        _log.error("clientes_nuevos: %s", e)
        clientes_nuevos = 0

    try:
        tasa_retorno = obtener_tasa_retorno(inicio, fin, id_negocio)
    except Exception as e:  # pragma: no cover
        _log.error("tasa_retorno: %s", e)
        tasa_retorno = {"total": 0, "recurrentes": 0, "tasa": 0}

    try:
        gasto_prom_cliente = obtener_gasto_promedio_cliente(inicio, fin, id_negocio)
    except Exception as e:  # pragma: no cover
        _log.error("gasto_prom_cliente: %s", e)
        gasto_prom_cliente = 0.0

    return {
        "ventas_semanales":   ventas_semanales,
        "gastos_semanales":   gastos_semanales,
        "ingresos_semanales": ingresos_semanales,
        "unidades_semanales": unidades_semanales,
        "ventas_prepago":     ventas_prepago,
        "uso_servicios":      uso_servicios,
        "ventas_por_dia":     ventas_por_dia,
        "top_clientes":       top_clientes,
        "tiempo_entrega":     tiempo_entrega,
        "ingresos_x_negocio": ingresos_x_negocio,
        "metodos_pago":       metodos_pago,
        "hora_recepcion":     hora_recepcion,
        "hora_entrega":       hora_entrega,
        "clientes_unicos":    clientes_unicos,
        "clientes_nuevos":    clientes_nuevos,
        "tasa_retorno":       tasa_retorno,
        "gasto_prom_cliente": gasto_prom_cliente,
        "calzado_marcas":     calzado_marcas,
        "calzado_tipos":      calzado_tipos,
    }


def exportar_estadisticas_service(args):
    """(Workbook, None) con KPIs y series del periodo, o (None, mensaje de error)."""
    inicio_str = args.get("inicio")
    fin_str    = args.get("fin")
    id_negocio = args.get("id_negocio", "all")

    if not inicio_str or not fin_str:
        return None, "Faltan fechas"
    try:
        inicio = datetime.strptime(inicio_str, "%Y-%m-%d").date()
        fin    = datetime.strptime(fin_str,    "%Y-%m-%d").date()
    except ValueError:
        return None, "Formato de fecha inválido"
    if fin < inicio:
        return None, "La fecha fin no puede ser menor a inicio"
    if (fin - inicio).days >= MAX_DIAS_ANIO:
        return None, "El rango máximo permitido es de un año"

    from openpyxl import Workbook
    from services.excel_helpers import (
        C, xl_cell, xl_titulo_hoja, xl_fila_headers, xl_col_widths
    )

    kpis   = _calcular_kpis(inicio, fin, id_negocio)
    dias   = (fin - inicio).days
    series = _cargar_series(inicio, fin, id_negocio,
                            "dia" if dias <= 31 else "semana" if dias <= MAX_DIAS_RANGO else "mes")

    negocio_label = {"1": "Calzado", "2": "Confección", "3": "Maquila"}.get(str(id_negocio), "Todos los negocios")
    subtitulo = f"{inicio_str} al {fin_str} — {negocio_label}"

    wb = Workbook()

    # ── Hoja 1: KPIs ──
    ws1 = wb.active
    ws1.title = "Resumen"
    xl_titulo_hoja(ws1, "Estadísticas Fresh Steps", 2, subtitulo)
    xl_fila_headers(ws1, ["Indicador", "Valor"], fila=3)

    kpi_rows = [
        ("Ingresos",          kpis["ingresos"],         '#,##0.00'),
        ("Gastos",            kpis["gastos"],            '#,##0.00'),
        ("Ganancia",          kpis["ganancia"],          '#,##0.00'),
        ("Total de ventas",   kpis["num_ventas"],        '#,##0'),
        ("Ticket promedio",   kpis["ticket_promedio"],   '#,##0.00'),
        ("Saldo por cobrar",  kpis["saldo_por_cobrar"],  '#,##0.00'),
    ]
    for i, (label, value, fmt) in enumerate(kpi_rows, 4):
        bg = C["gris"] if i % 2 == 0 else C["blanco"]
        xl_cell(ws1, i, 1, label, fg=bg)
        xl_cell(ws1, i, 2, value, fg=bg, align="right", num_fmt=fmt)
    xl_col_widths(ws1, {1: 24, 2: 18})

    # ── Hoja 2: Series ──
    ws2 = wb.create_sheet("Series por período")
    labels    = [r["label"] for r in series.get("ventas_semanales", [])]
    ventas    = [r["total"] for r in series.get("ventas_semanales", [])]
    ingresos  = [r["total"] for r in series.get("ingresos_semanales", [])]
    unidades  = [r["total"] for r in series.get("unidades_semanales", [])]

    xl_titulo_hoja(ws2, "Series por período", 4, subtitulo)
    xl_fila_headers(ws2, ["Período", "Ventas", "Ingresos ($)", "Unidades"], fila=3)
    for i, lbl in enumerate(labels):
        row = i + 4
        bg  = C["gris"] if i % 2 == 0 else C["blanco"]
        xl_cell(ws2, row, 1, lbl,             fg=bg)
        xl_cell(ws2, row, 2, ventas[i],       fg=bg, align="right", num_fmt='#,##0')
        xl_cell(ws2, row, 3, ingresos[i],     fg=bg, align="right", num_fmt='#,##0.00')
        xl_cell(ws2, row, 4, unidades[i],     fg=bg, align="right", num_fmt='#,##0')
    xl_col_widths(ws2, {1: 20, 2: 12, 3: 16, 4: 12})

    return wb, None


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

    modo = args.get("modo")
    if modo not in _MODOS:
        modo = None

    if modo == "anio":
        if inicio.year != fin.year:
            return None, "El modo Año abarca un solo año calendario"
    elif (fin - inicio).days > MAX_DIAS_RANGO:
        return None, f"El rango máximo permitido es {MAX_DIAS_RANGO} días (~6 meses)"

    agrupacion_gastos = args.get("agrupacion_gastos", "proveedor")
    if agrupacion_gastos not in {"proveedor", "categoria"}:
        agrupacion_gastos = "proveedor"

    granularidad = args.get("granularidad", "semana")
    if modo == "anio":
        granularidad = "mes"
    elif granularidad == "mes":
        granularidad = "semana"   # por mes solo en modo Año

    kpis   = _calcular_kpis(inicio, fin, id_negocio)
    pcts, periodo_anterior_str, periodo_actual_str = _calcular_comparativa(kpis, inicio, fin, id_negocio, modo)
    series = _cargar_series(inicio, fin, id_negocio, granularidad, agrupacion_gastos)

    return {
        **series,
        "periodo_actual":   periodo_actual_str,
        "periodo_anterior": periodo_anterior_str,
        "kpis":             {**kpis, **pcts},
    }, None


def kpis_inicio_service(negocio, es_admin: bool) -> dict:
    """KPIs de la pantalla de inicio. `negocio`: 'all', un id o la lista de ids de la caja."""
    hoy_dt         = date.today()
    negocio_filtro = negocio if negocio != "all" else None

    total_entregas, total_pendientes = contar_entregas_resumen(id_negocio=negocio_filtro)

    lunes         = hoy_dt - timedelta(days=hoy_dt.weekday())
    sabado        = lunes + timedelta(days=5)
    ventas_semana   = contar_ventas_por_dia_rango(lunes, sabado, negocio)
    unidades_semana = contar_unidades_por_dia_rango(lunes, sabado, negocio)
    ventas_hoy      = contar_ventas_por_dia_rango(hoy_dt, hoy_dt, negocio)[0]["total"]

    unidades_recibidas_hoy  = contar_unidades_hoy("fecha_recibo",  negocio)
    unidades_entregadas_hoy = contar_unidades_hoy("fecha_entrega", negocio)
    ventas_entregadas_hoy   = contar_ventas_entregadas_hoy(negocio)

    ingresos_hoy = None
    kpis_mes     = None
    if es_admin:
        ingresos_hoy   = float(obtener_total_ingresos(hoy_dt, hoy_dt, negocio))
        primer_dia_mes = date(hoy_dt.year, hoy_dt.month, 1)
        ing_mes  = float(obtener_total_ingresos(primer_dia_mes, hoy_dt, negocio))
        gas_mes  = float(obtener_total_gastos(primer_dia_mes, hoy_dt, negocio))
        kpis_mes = {"ingresos": ing_mes, "gastos": gas_mes, "ganancia": ing_mes - gas_mes}

    return {
        "total_entregas":          total_entregas,
        "total_pendientes":        total_pendientes,
        "ventas_hoy":              ventas_hoy,
        "chart_labels":            [x["label"] for x in ventas_semana],
        "chart_data":              [x["total"]  for x in ventas_semana],
        "chart_unidades":          [x["total"]  for x in unidades_semana],
        "chart_hoy_idx":           hoy_dt.weekday(),
        "unidades_recibidas_hoy":  unidades_recibidas_hoy,
        "unidades_entregadas_hoy": unidades_entregadas_hoy,
        "ventas_entregadas_hoy":   ventas_entregadas_hoy,
        "ingresos_hoy":            ingresos_hoy,
        "kpis_mes":                kpis_mes,
    }
