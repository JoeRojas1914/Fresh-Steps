import { abrirModal, cerrarModal } from '../components/modal.js';
import { initModalForm, mostrarFeedback, crearEliminarHandler, shakeEl, escapeHtml, csrfFetch, apiAction } from '../base/helpers.js';
import { validarRequerido, validarPrecio } from '../base/form_validators.js';
import { renderDiff, abrirHistorial } from '../base/historial_helpers.js';

document.addEventListener("DOMContentLoaded", () => {
    const form      = document.getElementById("formServicio");
    const submitBtn = document.querySelector('[form="formServicio"][type="submit"]');
    const modalEl   = document.getElementById("modalServicio");

    let revalidate = () => {};
    if (form && submitBtn) {
        revalidate = initModalForm(form, submitBtn);
        modalEl?.addEventListener("modal:opened", () => revalidate());
    }

    if (form) {
        form.addEventListener("submit", function (e) {
            const negocio = form.querySelector("[name=id_negocio]").value;
            const nombre  = form.querySelector("[name=nombre]").value;
            const precio  = form.querySelector("[name=precio]").value;

            if (!validarRequerido(negocio) || !validarRequerido(nombre) || !validarRequerido(precio)) {
                mostrarFeedback("Negocio, nombre y precio son obligatorios.", "error");
                shakeEl(form);
                e.preventDefault();
                return;
            }

            if (!validarPrecio(precio)) {
                mostrarFeedback("El precio no puede ser negativo.", "error");
                shakeEl(form.querySelector("[name=precio]"));
                e.preventDefault();
                return;
            }

            if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Guardando..."; }
        });
    }

    const formFiltro = document.getElementById("form-filtro-servicios");
    const container  = document.getElementById("tabla-paginada");
    if (formFiltro && container) window.initFiltroAjax(formFiltro, container);
});


let _defaultPendiente = null;

document.addEventListener("click", (e) => {
    const btn = e.target.closest(".js-default-servicio");
    if (!btn || btn.disabled) return;

    const anterior = btn.dataset.defaultActual;
    if (!anterior) { alternarDefault(btn); return; }

    _defaultPendiente = btn;
    document.getElementById("defaultNegocio").textContent  = btn.dataset.negocio;
    document.getElementById("defaultAnterior").textContent = anterior;
    document.getElementById("defaultNuevo").textContent    = btn.dataset.nombre;
    abrirModal("modalConfirmarDefaultServicio");
});

document.addEventListener("click", (e) => {
    if (!e.target.closest(".js-confirmar-default-servicio") || !_defaultPendiente) return;
    const btn = _defaultPendiente;
    _defaultPendiente = null;
    cerrarModal("modalConfirmarDefaultServicio");
    alternarDefault(btn);
});

async function alternarDefault(btn) {
    btn.disabled = true;
    try {
        const res  = await csrfFetch(`/servicios/${btn.dataset.id}/default`, { method: "POST" });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) {
            mostrarFeedback(data.error || "No se pudo cambiar el servicio predeterminado.", "error");
            btn.disabled = false;
            return;
        }
        mostrarFeedback(data.message, "success");
        const container = document.getElementById("tabla-paginada");
        if (container && window.cargarTablaAjax) {
            window.cargarTablaAjax(window.location.href, container, { push: false });
        } else {
            window.location.reload();
        }
    } catch {
        mostrarFeedback("Error de conexión.", "error");
        btn.disabled = false;
    }
}


const _eliminarServicio = crearEliminarHandler("modalConfirmarEliminarServicio");
function confirmarEliminarServicio(id) { _eliminarServicio.confirmar(`/servicios/eliminar/${id}`); }
function ejecutarEliminarServicio()    { _eliminarServicio.ejecutar(); }


function abrirNuevoServicio() {
    const f = document.getElementById("formServicio");
    if (f) f.reset();
    document.getElementById("id_servicio").value             = "";
    document.getElementById("modalServicio_title").innerText = "Agregar servicio";
    abrirModal("modalServicio");
}


function editarServicio(btn) {
    abrirModal("modalServicio");

    document.getElementById("modalServicio_title").innerText = "Editar servicio";

    document.getElementById("id_servicio").value         = btn.dataset.id;
    document.getElementById("id_negocio").value          = btn.dataset.negocio;
    document.querySelector("[name=nombre]").value        = btn.dataset.nombre;
    document.querySelector("[name=precio]").value        = btn.dataset.precio;
}


function verHistorialServicio(id) {
    abrirHistorial(
        `/servicios/${id}/historial`,
        "modalHistorialServicio",
        "#tablaHistorialServicio",
        h => renderDiff(h, "Servicio")
    );
}

document.addEventListener("click", function (e) {
    const btnNuevo = e.target.closest(".js-abrir-nuevo-servicio");
    if (btnNuevo) { abrirNuevoServicio(); return; }

    const btnEditar = e.target.closest(".js-editar-servicio");
    if (btnEditar) { editarServicio(btnEditar); return; }

    const btnHistorial = e.target.closest(".js-ver-historial-servicio");
    if (btnHistorial) { verHistorialServicio(parseInt(btnHistorial.dataset.id)); return; }

    const btnEliminar = e.target.closest(".js-confirmar-eliminar-servicio");
    if (btnEliminar) {
        const el = document.getElementById("servicioNombreEliminar");
        if (el) el.innerHTML = `¿Seguro que deseas eliminar?<br><span>${escapeHtml(btnEliminar.dataset.nombre)}</span>`;
        _eliminarServicio.confirmar(`/servicios/eliminar/${btnEliminar.dataset.id}`, btnEliminar.closest("tr"));
        return;
    }

    const btnEjecutar = e.target.closest(".js-ejecutar-eliminar-servicio");
    if (btnEjecutar) { ejecutarEliminarServicio(); return; }

    // La ruta solo acepta POST y responde JSON (antes era un enlace GET y daba 405)
    const btnRestaurar = e.target.closest(".js-restaurar-servicio");
    if (btnRestaurar) {
        apiAction({
            url: `/servicios/restaurar/${btnRestaurar.dataset.id}`,
            msgError: "No se pudo restaurar el servicio.",
            loadingBtn: btnRestaurar,
            reload: true,
            reloadDelay: 300,
        });
        return;
    }
});
