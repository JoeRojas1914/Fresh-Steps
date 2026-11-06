import { escapeHtml, fmtDinero } from '../base/helpers.js';

const _ICONO_ARTICULO = { calzado: "footprints", confeccion: "scissors", maquila: "factory" };

function _caracteristicas(d) {
    const partes = [];
    const colores = [d.color_base, d.color_secundario].filter(Boolean).join(" / ");
    if (colores)         partes.push(colores);
    if (d.color_agujetas) partes.push(`agujetas ${d.color_agujetas}`);
    if (d.material)       partes.push(d.material);
    return partes.map(escapeHtml).join(", ") || '<span class="dim-soft">—</span>';
}


function _filasArticulo(item) {
    const d = item.datos || {};
    const icono = _ICONO_ARTICULO[item.tipo_articulo] || "package";
    const esMaquila = item.tipo_articulo === "maquila";
    const nombre = [d.tipo, esMaquila ? null : d.marca].filter(Boolean).map(escapeHtml).join(" ") || "Artículo";
    const cantidad = d.cantidad && Number(d.cantidad) > 1 ? ` <span class="dt-cant">×${escapeHtml(d.cantidad)}</span>` : "";

    let servicios = (item.servicios || []).map(s => [escapeHtml(s.nombre), fmtDinero(s.precio_aplicado)]);
    if (esMaquila) {
        const cant = Number(d.cantidad || 0);
        const unit = Number(d.precio_unitario || 0);
        servicios = [[`${cant} × ${fmtDinero(unit)}`, fmtDinero(cant * unit)]];
    }
    if (!servicios.length) servicios = [['<span class="dim-soft">Sin servicios</span>', ""]];

    const n = servicios.length;
    const filas = servicios.map(([serv, precio], i) => `
        <tr>
            ${i === 0 ? `
            <td class="dt-articulo" rowspan="${n}">
                <span class="dt-icono"><i data-lucide="${icono}" width="14" height="14"></i></span>
                <span>${nombre}${cantidad}</span>
            </td>
            <td class="dt-caract" rowspan="${n}">${esMaquila ? '<span class="dim-soft">—</span>' : _caracteristicas(d)}</td>` : ""}
            <td>${serv}</td>
            <td class="dt-precio">${precio}</td>
        </tr>`).join("");

    const nota = item.comentario ? `
        <tr class="dt-nota-fila">
            <td colspan="4">
                <span class="dt-nota"><i data-lucide="message-circle" width="13" height="13"></i> ${escapeHtml(item.comentario)}</span>
            </td>
        </tr>` : "";

    return `<tbody class="dt-grupo">${filas}${nota}</tbody>`;
}

function _tablaDetalles(detalles, total, descuento) {
    const desc = Number(descuento || 0);
    const tieneTotal = total !== undefined && total !== "";
    let pie = "";
    if (tieneTotal && desc > 0) {
        pie = `
        <tfoot>
            <tr class="dt-subtotal">
                <td colspan="3">Subtotal</td>
                <td class="dt-precio">${fmtDinero(Number(total) + desc)}</td>
            </tr>
            <tr class="dt-descuento">
                <td colspan="3">Descuento</td>
                <td class="dt-precio">−${fmtDinero(desc)}</td>
            </tr>
            <tr class="dt-total">
                <td colspan="3">Total de la venta</td>
                <td class="dt-precio">${fmtDinero(total)}</td>
            </tr>
        </tfoot>`;
    } else if (tieneTotal) {
        pie = `
        <tfoot>
            <tr class="dt-total">
                <td colspan="3">Total de la venta</td>
                <td class="dt-precio">${fmtDinero(total)}</td>
            </tr>
        </tfoot>`;
    }
    return `
        <li class="detalles-tabla-wrap">
            <table class="detalles-tabla">
                <thead>
                    <tr>
                        <th>Artículo</th>
                        <th>Características</th>
                        <th>Servicio</th>
                        <th class="dt-precio">Precio</th>
                    </tr>
                </thead>
                ${detalles.map(_filasArticulo).join("")}
                ${pie}
            </table>
        </li>`;
}

document.addEventListener("click", function (e) {
    const btn = e.target.closest(".btn-detalles[data-id]");
    if (btn) { toggleDetalles(btn.dataset.id, btn); return; }

    const ticket = e.target.closest(".js-ver-ticket");
    if (ticket) { window.open(ticket.dataset.url, "_blank"); }
});

export function toggleDetalles(idVenta, btn) {
    const fila  = document.getElementById(`detalles-${idVenta}`);
    const lista = document.getElementById(`lista-detalles-${idVenta}`);

    if (!fila || !lista) return;

    const visible = fila.style.display === "table-row";
    const chevron = btn ? btn.querySelector(".chevron-icon") : null;

    if (visible) {
        const box = fila.querySelector(".detalles-box");
        if (chevron) chevron.classList.remove("chevron-icon--abierto");
        if (box) {
            box.classList.add("detalles-box--closing");
            box.addEventListener("animationend", () => {
                fila.style.display = "none";
                box.classList.remove("detalles-box--closing");
            }, { once: true });
        } else {
            fila.style.display = "none";
        }
        return;
    }

    fila.style.display = "table-row";
    if (chevron) chevron.classList.add("chevron-icon--abierto");

    if (lista.dataset.cargado) return;

    lista.innerHTML = window.Skeleton ? window.Skeleton.lineas(2) : `<li class="dim-soft">Cargando...</li>`;

    fetch(`/ventas/detalles/${idVenta}`)
        .then(r => r.json())
        .then(detalles => {

            lista.dataset.cargado = "1";

            if (!detalles.length) {
                lista.innerHTML = `<li class="detalle-vacio">Esta venta no tiene artículos registrados.</li>`;
                return;
            }

            lista.innerHTML = _tablaDetalles(detalles, lista.dataset.total, lista.dataset.descuento);
            if (window.lucide) lucide.createIcons();
        })
        .catch(() => {
            lista.innerHTML = `<li class="detalle-vacio">No se pudieron cargar los detalles. Intenta de nuevo.</li>`;
        });
}
