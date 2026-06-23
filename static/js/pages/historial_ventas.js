import { abrirModal } from '../components/modal.js';
import { escapeHtml } from '../base/helpers.js';
import { toggleDetalles } from './detalles_venta.js';

document.addEventListener("click", function (e) {
    const btn = e.target.closest(".btn-historial-venta");
    if (btn) verHistorialVenta(btn.dataset.id);
});

document.addEventListener("DOMContentLoaded", () => {

    const toggleEliminadas = document.getElementById("toggle-eliminadas");
    if (toggleEliminadas) {
        toggleEliminadas.addEventListener("change", () => {
            const url = new URL(window.location.href);
            if (toggleEliminadas.checked) {
                url.searchParams.set("eliminadas", "1");
            } else {
                url.searchParams.delete("eliminadas");
            }
            window.location.href = url.toString();
        });
    }

});

async function verHistorialVenta(idVenta) {
    abrirModal("modalHistorialVenta");

    const tbody = document.querySelector("#tablaHistorialVenta tbody");
    tbody.innerHTML = "<tr><td colspan='4' class='text-center dim'>Cargando...</td></tr>";

    try {
        const res  = await fetch(`/ventas/${idVenta}/historial`);
        if (!res.ok) throw new Error("Error de red");
        const data = await res.json();

        if (!data.length) {
            tbody.innerHTML = "<tr><td colspan='4' class='text-center dim'>Sin historial registrado</td></tr>";
            return;
        }

        const ACCIONES_VALIDAS = new Set(["CREADO", "LISTA", "ENTREGADO", "ELIMINADO", "REVERTIDO", "EDITADO"]);

        tbody.innerHTML = data.map(h => {
            const accion = ACCIONES_VALIDAS.has(h.accion) ? h.accion : "DESCONOCIDO";
            const fecha  = new Date(h.fecha).toLocaleString("es-MX");

            let detalle = "—";
            if (accion === "CREADO" && h.datos_despues) {
                try {
                    const d = JSON.parse(h.datos_despues);
                    detalle = `Total: $${parseFloat(d.total || 0).toFixed(2)}`;
                } catch {}
            }
            if (accion === "EDITADO" && h.datos_antes && h.datos_despues) {
                try {
                    const a    = JSON.parse(h.datos_antes);
                    const d    = JSON.parse(h.datos_despues);
                    const fmt$ = v => `$${parseFloat(v || 0).toFixed(2)}`;
                    const fmtF = s => {
                        if (!s) return "—";
                        const [fecha, hora] = String(s).split(" ");
                        const [y, m, dy]    = (fecha || "").split("-");
                        const mes = ["ene","feb","mar","abr","may","jun",
                                     "jul","ago","sep","oct","nov","dic"][parseInt(m,10)-1] || m;
                        const h5  = hora ? hora.slice(0,5) : "";
                        return h5 ? `${parseInt(dy,10)} ${mes} ${y} ${h5}` : `${parseInt(dy,10)} ${mes} ${y}`;
                    };
                    const partes = [];

                    if (d.fecha_estimada && a.fecha_estimada !== d.fecha_estimada) {
                        partes.push(`Fecha: ${fmtF(a.fecha_estimada)} → ${fmtF(d.fecha_estimada)}`);
                    }
                    if (parseFloat(d.delta_total || 0) !== 0) {
                        const delta = parseFloat(d.delta_total);
                        partes.push(`Total: ${fmt$(a.total)} → ${fmt$(d.total)} (${delta > 0 ? "+" : ""}${fmt$(delta)})`);
                    }
                    if (d.nuevos_arts > 0) {
                        partes.push(`+${d.nuevos_arts} artículo${d.nuevos_arts > 1 ? "s" : ""} nuevo${d.nuevos_arts > 1 ? "s" : ""}`);
                    }
                    if (d.nuevos_srv > 0) {
                        partes.push(`+${d.nuevos_srv} servicio${d.nuevos_srv > 1 ? "s" : ""} nuevo${d.nuevos_srv > 1 ? "s" : ""}`);
                    }
                    if (d.precios_editados?.length > 0) {
                        const items = d.precios_editados.map(e =>
                            `${escapeHtml(e.nombre)}: ${fmt$(e.precio_antes)} → ${fmt$(e.precio_nuevo)}`
                        ).join(", ");
                        partes.push(`Precio${d.precios_editados.length > 1 ? "s" : ""} editado${d.precios_editados.length > 1 ? "s" : ""}: ${items}`);
                    }
                    if (d.servicios_eliminados?.length > 0) {
                        const items = d.servicios_eliminados.map(e =>
                            `${escapeHtml(e.nombre)} (${fmt$(e.precio)})`
                        ).join(", ");
                        partes.push(`Eliminado${d.servicios_eliminados.length > 1 ? "s" : ""}: ${items}`);
                    }
                    if (d.detalles_arts_editados?.length > 0) {
                        const etiquetas = {
                            tipo: "Tipo", marca: "Marca", material: "Material",
                            color_base: "Color base", color_secundario: "Color sec.",
                            color_agujetas: "Color agujetas",
                            cantidad: "Cantidad", precio_unitario: "P. unitario",
                        };
                        const items = d.detalles_arts_editados.map(a => {
                            const cs = a.cambios.map(c =>
                                `${etiquetas[c.campo] || c.campo}: ${escapeHtml(c.antes) || "(vacío)"} → ${escapeHtml(c.despues) || "(vacío)"}`
                            ).join(", ");
                            return `Art. #${a.num} (${a.tipo}): ${cs}`;
                        }).join(" | ");
                        partes.push(`Campos editados — ${items}`);
                    }
                    detalle = partes.length ? partes.join(" | ") : "Sin cambios de precio";
                } catch {}
            }

            return `<tr>
                <td><span class="accion-badge accion--${accion.toLowerCase()}">${escapeHtml(accion)}</span></td>
                <td>${escapeHtml(h.usuario || "—")}</td>
                <td>${fecha}</td>
                <td>${detalle}</td>
            </tr>`;
        }).join("");
    } catch {
        tbody.innerHTML = "<tr><td colspan='4' class='text-center dim'>Error al cargar historial.</td></tr>";
    }
}
