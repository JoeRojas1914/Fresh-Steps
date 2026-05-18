import { abrirModal, cerrarModal } from '../components/modal.js';
import { mostrarFeedback, csrfFetch, confirmarEliminarVenta } from '../base/helpers.js';

document.addEventListener("DOMContentLoaded", () => {

    let ventaSeleccionada = null;

    document.querySelectorAll(".btn-marcar-lista").forEach(btn => {
        btn.addEventListener("click", () => {
            ventaSeleccionada = btn.dataset.id;
            abrirModal("modalProcesado");
        });
    });

    const btnConfirmar = document.getElementById("btnConfirmarLista");

    if (btnConfirmar) {
        btnConfirmar.addEventListener("click", () => {

            if (!ventaSeleccionada) return;

            csrfFetch(`/ventas/marcar-lista/${ventaSeleccionada}`, { method: "POST" })
                .then(r => r.json())
                .then(res => {
                    if (res.ok) {
                        cerrarModal("modalProcesado");
                        mostrarFeedback(res.message, "success");
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        mostrarFeedback(res.error || "Error al marcar como lista", "error");
                    }
                })
                .catch(() => mostrarFeedback("Error de conexión al marcar la venta.", "error"));
        });
    }

    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".btn-eliminar");
        if (!btn) return;
        confirmarEliminarVenta(btn.dataset.id);
    });

});
