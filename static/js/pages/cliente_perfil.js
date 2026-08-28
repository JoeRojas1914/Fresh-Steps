import { initModalForm, mostrarFeedback, shakeEl } from '../base/helpers.js';
import { validarRequerido, validarTelefono } from '../base/form_validators.js';

// ── AJAX filter & "Limpiar" ──────────────────────────────────
(function () {
    const form      = document.getElementById('form-filtro-cliente');
    const container = document.getElementById('tabla-paginada');
    const clearEl   = document.getElementById('btn-limpiar-filtro');

    window.initFiltroAjax(form, container, { clearEl });
})();

// ── Edit modal validation ────────────────────────────────────
const editForm  = document.getElementById('modalEditarClienteForm');
const submitBtn = document.querySelector('[form="modalEditarClienteForm"][type="submit"]');
const modalEl   = document.getElementById('modalEditarCliente');

if (editForm && submitBtn) {
    const revalidate = initModalForm(editForm, submitBtn);
    modalEl?.addEventListener('modal:opened', () => revalidate());

    editForm.addEventListener('submit', function (e) {
        const nombre   = editForm.querySelector('[name=nombre]').value;
        const apellido = editForm.querySelector('[name=apellido]').value;
        const telefono = editForm.querySelector('[name=telefono]').value;

        if (!validarRequerido(nombre) || !validarRequerido(apellido) || !validarRequerido(telefono)) {
            mostrarFeedback('Nombre, apellido y teléfono son obligatorios.', 'error');
            shakeEl(editForm);
            e.preventDefault();
            return;
        }
        if (!validarTelefono(telefono)) {
            mostrarFeedback('El teléfono debe tener exactamente 10 dígitos.', 'error');
            shakeEl(editForm.querySelector('[name=telefono]'));
            e.preventDefault();
            return;
        }
        if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Guardando...'; }
    });
}