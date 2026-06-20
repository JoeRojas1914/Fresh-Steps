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

        const ACCIONES_VALIDAS = new Set(["CREADO", "LISTA", "ENTREGADO", "ELIMINADO", "REVERTIDO"]);

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
