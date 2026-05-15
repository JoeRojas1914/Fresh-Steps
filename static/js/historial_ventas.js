document.addEventListener("DOMContentLoaded", () => {

    document.querySelectorAll(".btn--info[data-id]").forEach(btn => {
        btn.addEventListener("click", () => toggleDetalles(btn.dataset.id));
    });

    document.querySelectorAll(".btn-historial-venta").forEach(btn => {
        btn.addEventListener("click", () => verHistorialVenta(btn.dataset.id));
    });

});

async function verHistorialVenta(idVenta) {
    abrirModal("modalHistorialVenta");

    const tbody = document.querySelector("#tablaHistorialVenta tbody");
    tbody.innerHTML = "<tr><td colspan='4' style='text-align:center;opacity:.5;'>Cargando...</td></tr>";

    try {
    const res  = await fetch(`/ventas/${idVenta}/historial`);
    if (!res.ok) throw new Error("Error de red");
    const data = await res.json();

    if (!data.length) {
        tbody.innerHTML = "<tr><td colspan='4' style='text-align:center;opacity:.5;'>Sin historial registrado</td></tr>";
        return;
    }

    const iconos = {
        CREADO:    "",
        LISTA:     "",
        ENTREGADO: "",
        ELIMINADO: "",
    };

    const colores = {
        CREADO:    "#1e7fd6",
        LISTA:     "#f59e0b",
        ENTREGADO: "#22c55e",
        ELIMINADO: "#ef4444",
    };

    tbody.innerHTML = data.map(h => {
        const icono  = iconos[h.accion]  || "•";
        const color  = colores[h.accion] || "#6b7280";
        const fecha  = new Date(h.fecha).toLocaleString("es-MX");

        let detalle = "—";
        if (h.accion === "CREADO" && h.datos_despues) {
            try {
                const d = JSON.parse(h.datos_despues);
                detalle = `Total: $${parseFloat(d.total || 0).toFixed(2)}`;
            } catch {}
        }

        return `<tr>
            <td><span style="font-weight:700;color:${color}">${escapeHtml(h.accion)}</span></td>
            <td>${escapeHtml(h.usuario || "—")}</td>
            <td>${fecha}</td>
            <td>${detalle}</td>
        </tr>`;
    }).join("");
    } catch {
        tbody.innerHTML = "<tr><td colspan='4' style='text-align:center;opacity:.5;'>Error al cargar historial.</td></tr>";
    }
}