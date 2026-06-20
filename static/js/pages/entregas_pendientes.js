import { abrirModal, cerrarModal } from '../components/modal.js';
import { mostrarFeedback, recargarConFeedback, csrfFetch, confirmarEliminarVenta } from '../base/helpers.js';
import { abrirWhatsApp } from '../base/whatsapp.js';

let ventaSeleccionada = null;
let ventaTelefono     = '';
let ventaNombre       = '';
let ventaNegocioId    = 0;
let ventaNegocio      = '';

document.addEventListener("click", function (e) {
    const btn = e.target.closest(".btn-marcar-lista");
    if (!btn) return;

    const waCheckbox  = document.getElementById("waCheckbox");
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

document.addEventListener("DOMContentLoaded", () => {

    const btnConfirmar = document.getElementById("btnConfirmarLista");

    if (btnConfirmar) {
        btnConfirmar.addEventListener("click", () => {

            if (!ventaSeleccionada || btnConfirmar.disabled) return;

            const textoOriginal = btnConfirmar.textContent;
            btnConfirmar.disabled    = true;
            btnConfirmar.textContent = "Procesando...";

            csrfFetch(`/ventas/marcar-lista/${ventaSeleccionada}`, { method: "POST" })
                .then(r => r.json())
                .then(res => {
                    if (res.ok) {
                        cerrarModal("modalProcesado");

                        const waCheckbox = document.getElementById("waCheckbox");
                        if (waCheckbox && waCheckbox.checked && ventaTelefono) {
                            const articulo = ventaNegocioId === 1 ? 'calzado' : 'prendas';
                            const msg = `Buen día ${ventaNombre},\nTu orden ha sido procesada, puedes pasar a recoger tu ${articulo} a partir de este momento.\nSaludos`;
                            abrirWhatsApp(ventaTelefono, msg, ventaNegocioId)
                                .then(r => { if (!r.ok) mostrarFeedback("No se pudo abrir WhatsApp", "error"); });
                        }
                        recargarConFeedback(res.message, "success");
                    } else {
                        btnConfirmar.disabled    = false;
                        btnConfirmar.textContent = textoOriginal;
                        mostrarFeedback(res.error || "Error al marcar como lista", "error");
                    }
                })
                .catch(() => {
                    btnConfirmar.disabled    = false;
                    btnConfirmar.textContent = textoOriginal;
                    mostrarFeedback("Error de conexión al marcar la venta.", "error");
                });
        });
    }

    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".btn-eliminar");
        if (!btn) return;
        confirmarEliminarVenta(btn.dataset.id);
    });

});
