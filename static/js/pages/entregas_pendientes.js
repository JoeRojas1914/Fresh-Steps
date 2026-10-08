import { abrirModal, cerrarModal } from '../components/modal.js';
import { mostrarFeedback, redirigirConFeedback, csrfFetch, confirmarEliminarVenta } from '../base/helpers.js';
import { abrirWhatsApp, preabrirVentanaWhatsApp, cerrarVentanaPrevia } from '../base/whatsapp.js';

const NEGOCIO_FRESH_STEPS = 1;

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

    const esFreshSteps = ventaNegocioId === NEGOCIO_FRESH_STEPS;
    const waRow = waCheckbox ? waCheckbox.closest(".wa-check-row") : null;
    if (waRow) waRow.style.display = esFreshSteps ? "" : "none";

    if (waCheckbox) {
        waCheckbox.checked  = esFreshSteps && !!ventaTelefono;
        waCheckbox.disabled = !esFreshSteps || !ventaTelefono;
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

            const waCheckbox = document.getElementById("waCheckbox");
            const enviarWa   = ventaNegocioId === NEGOCIO_FRESH_STEPS
                && waCheckbox && waCheckbox.checked && !!ventaTelefono;

            const ventanaWa = enviarWa ? preabrirVentanaWhatsApp() : null;

            csrfFetch(`/ventas/marcar-lista/${ventaSeleccionada}`, { method: "POST" })
                .then(r => r.json())
                .then(async res => {
                    if (res.ok) {
                        cerrarModal("modalProcesado");

                        if (enviarWa) {
                            const msg = `Buen día ${ventaNombre},\nTu orden ha sido procesada, puedes pasar a recoger tu calzado a partir de este momento.\nSaludos`;
                            const wa  = await abrirWhatsApp(ventaTelefono, msg, ventaNegocioId, ventanaWa);
                            if (!wa.ok) {
                                redirigirConFeedback(location.pathname, "Venta marcada como lista, pero no se pudo abrir WhatsApp", "error");
                                return;
                            }
                        }
                        redirigirConFeedback(location.pathname, res.message, "success");
                    } else {
                        cerrarVentanaPrevia(ventanaWa);
                        btnConfirmar.disabled    = false;
                        btnConfirmar.textContent = textoOriginal;
                        mostrarFeedback(res.error || "Error al marcar como lista", "error");
                    }
                })
                .catch(() => {
                    cerrarVentanaPrevia(ventanaWa);
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
