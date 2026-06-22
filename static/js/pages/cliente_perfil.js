import { initModalForm, mostrarFeedback, shakeEl } from '../base/helpers.js';
import { validarRequerido, validarTelefono } from '../base/form_validators.js';

// ── AJAX filter & "Limpiar" ──────────────────────────────────
(function () {
    const form      = document.getElementById('form-filtro-cliente');
    const container = document.getElementById('tabla-paginada');
    if (!form || !container) return;

    async function cargarTabla(pushUrl) {
        container.style.opacity       = '0.5';
        container.style.pointerEvents = 'none';
        try {
            const fetchUrl = new URL(pushUrl, window.location.href);
            fetchUrl.searchParams.set('partial', '1');
            const resp = await fetch(fetchUrl.toString());
            if (!resp.ok) throw new Error();
            container.innerHTML = await resp.text();
            history.pushState(null, '', pushUrl);
            if (window.lucide) window.lucide.createIcons();
        } catch {
            window.location.href = pushUrl;
        } finally {
            container.style.opacity       = '';
            container.style.pointerEvents = '';
        }
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const params = new URLSearchParams(new FormData(form));
        for (const [k, v] of [...params.entries()]) {
            if (!v) params.delete(k);
        }
        const url = params.toString()
            ? `${form.action}?${params}`
            : form.action;
        cargarTabla(url);
    });

    document.addEventListener('click', function (e) {
        const btn = e.target.closest('#btn-limpiar-filtro');
        if (!btn) return;
        e.preventDefault();
        form.querySelectorAll('select').forEach(s => { s.selectedIndex = 0; });
        form.querySelectorAll('input[type=date]').forEach(i => { i.value = ''; });
        cargarTabla(btn.href);
    });
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