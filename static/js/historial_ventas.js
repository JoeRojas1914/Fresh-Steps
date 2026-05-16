document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll(".btn-detalles[data-id]").forEach(btn => {
        btn.addEventListener("click", () => toggleDetalles(btn.dataset.id, btn));
    });

    document.querySelectorAll(".btn-historial-venta").forEach(btn => {
        btn.addEventListener("click", () => verHistorialVenta(btn.dataset.id));
    });

    const toggleEliminadas = document.getElementById("toggle-eliminadas");
    if (toggleEliminadas) {
        toggleEliminadas.addEventListener("change", () => toggleEliminadas.form.submit());
    }

});

async function verHistorialVenta(idVenta) {
    abrirModal("modalHistorialVenta");

    const tbody = document.querySelector("#tablaHistorialVenta tbody");
    tbody.innerHTML = "<tr><td colspan='4' class="text-center dim">Cargando...</td></tr>";

    try {
    const res  = await fetch(`/ventas/${idVenta}/historial`);
    if (!res.ok) throw new Error("Error de red");
    const data = await res.json();

    if (!data.length) {
        tbody.innerHTML = "<tr><td colspan='4' class="text-center dim">Sin historial registrado</td></tr>";
        return;
    }

    const ACCIONES_VALIDAS = new Set(["CREADO", "LISTA", "ENTREGADO", "ELIMINADO"]);

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
        tbody.innerHTML = "<tr><td colspan='4' class="text-center dim">Error al cargar historial.</td></tr>";
    }
}