import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from openpyxl import Workbook
from services.excel_helpers import (
    C, xl_cell, xl_row_bg, fmt_dt, estado_venta,
    xl_titulo_hoja, xl_fila_headers, xl_fila_totales,
    xl_col_widths, xl_badge_estado, xl_badge_activo, send_excel
)

from services.clientes_service import (
    listar_clientes_service,
    guardar_cliente_service,
    eliminar_cliente_service,
    restaurar_cliente_service,
    buscar_clientes_service,
    obtener_cliente_detalle_service,
    obtener_historial_cliente_service
)

clientes_bp = Blueprint("clientes", __name__)


@clientes_bp.route("/clientes")
def clientes():
    q = request.args.get("q", "")
    pagina = request.args.get("pagina", 1, type=int)
    incluir_eliminados = request.args.get("eliminados") == "1"
    data = listar_clientes_service(q=q, pagina=pagina, incluir_eliminados=incluir_eliminados)
    return render_template(
        "clientes.html",
        clientes=data["clientes"], q=q, pagina=pagina,
        total_paginas=data["total_paginas"],
        total_clientes=data["total_clientes"],
        incluir_eliminados=incluir_eliminados
    )


@clientes_bp.route("/clientes/guardar", methods=["POST"])
def guardar_cliente():
    id_usuario = session.get("id_usuario")
    resultado  = guardar_cliente_service(request.form, id_usuario)
    flash(
        "✅ Cliente actualizado correctamente." if resultado == "actualizado"
        else "✅ Cliente creado correctamente.", "success"
    )
    return redirect(url_for("clientes.clientes"))


@clientes_bp.route("/clientes/eliminar/<int:id_cliente>")
def eliminar_cliente(id_cliente):
    id_usuario = session.get("id_usuario")
    ok = eliminar_cliente_service(id_cliente, id_usuario)
    if not ok:
        flash("❌ No puedes eliminar el cliente porque ya tiene ventas registradas.", "error")
    else:
        flash("🗑️ Cliente eliminado correctamente.", "success")
    return redirect(url_for("clientes.clientes"))


@clientes_bp.route("/clientes/restaurar/<int:id_cliente>")
def restaurar_cliente(id_cliente):
    id_usuario = session.get("id_usuario")
    restaurar_cliente_service(id_cliente, id_usuario)
    flash("♻️ Cliente restaurado correctamente.", "success")
    return redirect(url_for("clientes.clientes"))


@clientes_bp.route("/clientes/<int:id_cliente>/historial")
def historial_cliente(id_cliente):
    return jsonify(obtener_historial_cliente_service(id_cliente))


@clientes_bp.route("/api/clientes")
def api_clientes():
    q = request.args.get("q", "")
    return jsonify(buscar_clientes_service(q))


@clientes_bp.route("/clientes/<int:id_cliente>")
def ver_cliente(id_cliente):
    filtros = request.args
    data = obtener_cliente_detalle_service(id_cliente, filtros)
    return render_template("cliente_perfil.html", **data)


@clientes_bp.route("/api/clientes/crear", methods=["POST"])
def api_crear_cliente():
    id_usuario = session.get("id_usuario")
    cliente = guardar_cliente_service(request.form, id_usuario, api=True)
    return jsonify(cliente)


@clientes_bp.route("/clientes/exportar")
def exportar_clientes_excel():
    if session.get("rol") != "admin":
        return render_template("403.html"), 403
    from clientes import obtener_clientes

    incluir_eliminados = request.args.get("eliminados") == "1"
    clientes = obtener_clientes(limit=99999, offset=0, incluir_eliminados=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes"
    ws.freeze_panes = "A4"

    xl_titulo_hoja(ws, "Clientes — Fresh Steps", 6,
                   "Incluye eliminados" if incluir_eliminados else "Solo clientes activos")
    xl_fila_headers(ws, ["Nombre", "Apellido", "Teléfono", "Correo", "Dirección", "Estado"])

    for i, cl in enumerate(clientes):
        r  = i + 4
        bg = xl_row_bg(i)
        xl_cell(ws, r, 1, cl.get("nombre",    ""),  fg=bg, bold=True)
        xl_cell(ws, r, 2, cl.get("apellido",  ""),  fg=bg, bold=True)
        xl_cell(ws, r, 3, cl.get("telefono",  "—"), fg=bg)
        xl_cell(ws, r, 4, cl.get("correo",    "—"), fg=bg)
        xl_cell(ws, r, 5, cl.get("direccion", "—"), fg=bg)
        xl_badge_activo(ws, r, 6, cl.get("activo", 1))
        ws.row_dimensions[r].height = 16

    xl_col_widths(ws, [20, 20, 14, 28, 30, 11])
    return send_excel(wb, "clientes")


@clientes_bp.route("/clientes/<int:id_cliente>/exportar")
def exportar_cliente_excel(id_cliente):
    from ventas import obtener_ventas_cliente, obtener_detalles_venta
    from pagos import obtener_pagos_por_venta
    from clientes import obtener_cliente_por_id

    id_negocio   = request.args.get("id_negocio")  or None
    fecha_inicio = request.args.get("fecha_inicio") or None
    fecha_fin    = request.args.get("fecha_fin")    or None

    cliente      = obtener_cliente_por_id(id_cliente)
    pedidos      = obtener_ventas_cliente(id_cliente, id_negocio, fecha_inicio, fecha_fin, limit=99999, offset=0)
    ids_venta    = [p["id_venta"] for p in pedidos]
    detalles_map = obtener_detalles_venta(ids_venta)
    pagos_map    = {p["id_venta"]: obtener_pagos_por_venta(p["id_venta"]) for p in pedidos}

    nombre_cliente = f"{cliente['nombre']} {cliente['apellido']}"
    filtro_txt = "  ".join(filter(None, [
        f"Desde: {fecha_inicio}" if fecha_inicio else "",
        f"Hasta: {fecha_fin}"   if fecha_fin    else "",
    ])) or "Sin filtros de fecha"

    wb = Workbook()

    ws1 = wb.active
    ws1.title = "Resumen pedidos"
    ws1.freeze_panes = "A4"
    COLS1 = ["# Recibo","Negocio","Fecha recibo","Fecha estimada","Fecha lista","Fecha entrega","Total ($)","Cobrado ($)","Saldo ($)","Estado"]
    xl_titulo_hoja(ws1, f"Historial de pedidos — {nombre_cliente}", len(COLS1), filtro_txt)
    xl_fila_headers(ws1, COLS1)
    for i, p in enumerate(pedidos):
        r  = i + 4; bg = xl_row_bg(i)
        estado  = estado_venta(p)
        total   = float(p.get("total") or 0)
        pagos   = pagos_map.get(p["id_venta"], [])
        cobrado = sum(float(pg["monto"]) for pg in pagos)
        saldo   = max(total - cobrado, 0)
        xl_cell(ws1, r, 1, f"#{p['id_venta']}", fg=bg, bold=True, align="center")
        xl_cell(ws1, r, 2, p.get("negocio",""), fg=bg)
        xl_cell(ws1, r, 3, fmt_dt(p.get("fecha_recibo")), fg=bg)
        xl_cell(ws1, r, 4, fmt_dt(p.get("fecha_estimada")), fg=bg)
        xl_cell(ws1, r, 5, fmt_dt(p.get("fecha_lista")), fg=bg)
        xl_cell(ws1, r, 6, fmt_dt(p.get("fecha_entrega")), fg=bg)
        xl_cell(ws1, r, 7, total,   fg=bg, bold=True, align="right", num_fmt='"$"#,##0.00')
        xl_cell(ws1, r, 8, cobrado, fg=bg, bold=True, align="right", num_fmt='"$"#,##0.00')
        xl_cell(ws1, r, 9, saldo,   fg=bg, bold=True, align="right", num_fmt='"$"#,##0.00', color=C["rojo"] if saldo > 0 else C["verde"])
        xl_badge_estado(ws1, r, 10, estado)
        ws1.row_dimensions[r].height = 16
    if pedidos: xl_fila_totales(ws1, len(pedidos)+4, len(COLS1), [7,8,9])
    xl_col_widths(ws1, [10,18,20,20,18,18,13,13,13,13])

    ws2 = wb.create_sheet("Artículos")
    ws2.freeze_panes = "A4"
    COLS2 = ["# Recibo","Negocio","Tipo artículo","Descripción","Material / Notas","Cantidad","Servicio","Precio ($)","Comentario"]
    xl_titulo_hoja(ws2, f"Artículos — {nombre_cliente}", len(COLS2), filtro_txt)
    xl_fila_headers(ws2, COLS2)
    r2 = 4
    for p in pedidos:
        detalles = detalles_map.get(p["id_venta"], [])
        if not detalles:
            bg = xl_row_bg(r2)
            xl_cell(ws2, r2, 1, f"#{p['id_venta']}", fg=bg, bold=True, align="center")
            xl_cell(ws2, r2, 2, p.get("negocio",""), fg=bg)
            for ci in range(3,10): xl_cell(ws2, r2, ci, "—", fg=bg, color=C["gris_txt"], align="center")
            ws2.row_dimensions[r2].height = 15; r2 += 1; continue
        for det in detalles:
            tipo=det.get("tipo_articulo",""); datos=det.get("datos") or {}; coment=det.get("comentario") or ""; servicios=det.get("servicios",[])
            if tipo=="calzado":   desc=f"{datos.get('tipo','')} {datos.get('marca','')}".strip(); mat=f"Color: {datos.get('color_base','—')}  Material: {datos.get('material','—')}"; cant=1
            elif tipo=="confeccion": desc=f"{datos.get('tipo','')} {datos.get('marca','')}".strip(); mat=f"Material: {datos.get('material','—')}"; cant=datos.get("cantidad",1)
            elif tipo=="maquila": desc=datos.get("tipo","—"); mat=f"Precio unitario: ${float(datos.get('precio_unitario') or 0):.2f}"; cant=datos.get("cantidad",1)
            else: desc=mat="—"; cant="—"
            for si, svc in enumerate(servicios if servicios else [None]):
                bg=xl_row_bg(r2)
                xl_cell(ws2,r2,1,f"#{p['id_venta']}" if si==0 else "",fg=bg,bold=si==0,align="center")
                xl_cell(ws2,r2,2,p.get("negocio","") if si==0 else "",fg=bg)
                xl_cell(ws2,r2,3,tipo.capitalize() if si==0 else "",fg=bg,align="center")
                xl_cell(ws2,r2,4,desc if si==0 else "",fg=bg)
                xl_cell(ws2,r2,5,mat if si==0 else "",fg=bg,wrap=True)
                xl_cell(ws2,r2,6,cant if si==0 else "",fg=bg,align="center")
                xl_cell(ws2,r2,7,svc.get("nombre","") if svc else "—",fg=bg)
                xl_cell(ws2,r2,8,float(svc.get("precio_aplicado") or 0) if svc else "—",fg=bg,align="right",num_fmt='"$"#,##0.00' if svc else None)
                xl_cell(ws2,r2,9,coment if si==0 else "",fg=bg,wrap=True,italic=bool(coment))
                ws2.row_dimensions[r2].height=15; r2+=1
    xl_col_widths(ws2, [10,18,14,24,28,10,24,13,24])

    ws3 = wb.create_sheet("Pagos")
    ws3.freeze_panes = "A4"
    COLS3 = ["# Recibo","Negocio","Tipo pago","Método","Monto ($)","Total venta ($)"]
    xl_titulo_hoja(ws3, f"Pagos — {nombre_cliente}", len(COLS3), filtro_txt)
    xl_fila_headers(ws3, COLS3)
    r3 = 4
    for p in pedidos:
        pagos=pagos_map.get(p["id_venta"],[]); total=float(p.get("total") or 0)
        if not pagos:
            bg=xl_row_bg(r3)
            xl_cell(ws3,r3,1,f"#{p['id_venta']}",fg=bg,bold=True,align="center")
            xl_cell(ws3,r3,2,p.get("negocio",""),fg=bg)
            xl_cell(ws3,r3,3,"Sin pagos",fg=bg,color=C["gris_txt"],italic=True)
            xl_cell(ws3,r3,4,"—",fg=bg,align="center"); xl_cell(ws3,r3,5,"—",fg=bg,align="center")
            xl_cell(ws3,r3,6,total,fg=bg,align="right",num_fmt='"$"#,##0.00')
            ws3.row_dimensions[r3].height=15; r3+=1; continue
        for pi, pg in enumerate(pagos):
            bg=xl_row_bg(r3)
            xl_cell(ws3,r3,1,f"#{p['id_venta']}" if pi==0 else "",fg=bg,bold=pi==0,align="center")
            xl_cell(ws3,r3,2,p.get("negocio","") if pi==0 else "",fg=bg)
            xl_cell(ws3,r3,3,(pg.get("tipo_pago_venta") or "—").capitalize(),fg=bg)
            xl_cell(ws3,r3,4,(pg.get("tipo_pago") or "—").capitalize(),fg=bg)
            xl_cell(ws3,r3,5,float(pg.get("monto") or 0),fg=bg,bold=True,align="right",color=C["verde"],num_fmt='"$"#,##0.00')
            xl_cell(ws3,r3,6,total if pi==0 else "",fg=bg,align="right",num_fmt='"$"#,##0.00')
            ws3.row_dimensions[r3].height=15; r3+=1
    xl_col_widths(ws3, [10,18,16,16,14,14])

    nombre_archivo = f"pedidos_{cliente['nombre']}_{cliente['apellido']}".replace(" ","_")
    return send_excel(wb, nombre_archivo)