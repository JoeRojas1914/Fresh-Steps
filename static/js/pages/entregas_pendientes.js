import { abrirModal, cerrarModal } from '../components/modal.js';
import { mostrarFeedback, csrfFetch, confirmarEliminarVenta } from '../base/helpers.js';
import { abrirWhatsApp } from '../base/whatsapp.js';

document.addEventListener("DOMContentLoaded", () => {

    let ventaSeleccionada = null;
    let ventaTelefono     = '';
    let ventaNombre       = '';
    let ventaNegocioId    = 0;
    let ventaNegocio      = '';

    const waCheckbox = document.getElementById("waCheckbox");

    document.querySelectorAll(".btn-marcar-lista").forEach(btn => {
        btn.addEventListener("click", () => {
            ventaSeleccionada = btn.dataset.id;
            ventaTelefono     = btn.dataset.telefono  || '';
            ventaNombre       = btn.dataset.nombre     || '';
            ventaNegocioId    = parseInt(btn.dataset.negocioId) || 0;
            ventaNegocio      = btn.dataset.negocio    || '';

            if (waCheckbox) {
                waCheckbox.checked  = !!ventaTelefono;
                waCheckbox.disabled = !ventaTelefono;
            }

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

                        if (waCheckbox && waCheckbox.checked && ventaTelefono) {
                            const articulo = ventaNegocioId === 1 ? 'calzado' : 'prendas';
                            const msg = `Buen día ${ventaNombre},\nTu orden ha sido procesada, puedes pasar a recoger tu ${articulo} a partir de este momento.\nSaludos`;
                            abrirWhatsApp(ventaTelefono, msg, ventaNegocioId)
                                .then(r => { if (!r.ok) mostrarFeedback("No se pudo abrir WhatsApp", "error"); });
                        }
                        mostrarFeedback(res.message, "success");

                        setTimeout(() => location.reload(), 1500);
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
