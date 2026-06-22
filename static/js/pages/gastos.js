import { abrirModal } from '../components/modal.js';
import { initModalForm, mostrarFeedback, crearEliminarHandler, shakeEl, csrfFetch } from '../base/helpers.js';
import { validarRequerido, validarPrecio } from '../base/form_validators.js';
import { renderDiff, abrirHistorial } from '../base/historial_helpers.js';

document.addEventListener("DOMContentLoaded", () => {

    const toggleEliminados = document.getElementById("toggle-eliminados-gastos");
    if (toggleEliminados) {
        toggleEliminados.addEventListener("change", () => {
            const url = new URL(window.location.href);
            if (toggleEliminados.checked) {
                url.searchParams.set("eliminados", "1");
            } else {
                url.searchParams.delete("eliminados");
            }
            window.location.href = url.toString();
        });
    }

    const form      = document.getElementById("formGasto");
    const submitBtn = document.querySelector('[form="formGasto"][type="submit"]');
    const modalEl   = document.getElementById("modalGasto");

    let revalidate = () => {};
    if (form && submitBtn) {
        revalidate = initModalForm(form, submitBtn);
        modalEl?.addEventListener("modal:opened", () => revalidate());
    }

    if (!form) return;

    form.addEventListener("submit", function (e) {
        const descripcion = form.querySelector("[name=descripcion]").value;
        const proveedor   = form.querySelector("[name=proveedor]").value;
        const total       = form.querySelector("[name=total]").value;

        if (!validarRequerido(descripcion) || !validarRequerido(proveedor) || !validarRequerido(total)) {
            mostrarFeedback("Descripción, proveedor y total son obligatorios.", "error");
            shakeEl(form);
            e.preventDefault();
            return;
        }

        if (!validarPrecio(total)) {
            mostrarFeedback("El total no puede ser negativo.", "error");
            shakeEl(form.querySelector("[name=total]"));
            e.preventDefault();
            return;
        }

        if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Guardando..."; }
    });

});


const _eliminarGasto = crearEliminarHandler("modalConfirmarEliminarGasto");
function confirmarEliminarGasto(id) { _eliminarGasto.confirmar(`/gastos/eliminar/${id}`); }
function ejecutarEliminarGasto()    { _eliminarGasto.ejecutar(); }


function editarGasto(id, id_negocio, id_categoria, descripcion, proveedor, total, fecha_registro, tipo_comprobante, tipo_pago, notas) {
    document.getElementById("modalGasto_title").innerText   = "Editar gasto";
    document.getElementById("id_gasto").value               = id;
    document.getElementById("id_negocio").value             = id_negocio;
    document.getElementById("gasto_categoria").value        = id_categoria || "";
    document.querySelector("[name=descripcion]").value      = descripcion;
    document.querySelector("[name=proveedor]").value        = proveedor;
    document.querySelector("[name=total]").value            = total;
    document.querySelector("[name=fecha_registro]").value   = fecha_registro || "";
    document.querySelector("[name=tipo_comprobante]").value = tipo_comprobante;
    document.querySelector("[name=tipo_pago]").value        = tipo_pago;
    document.querySelector("[name=notas]").value            = notas || "";
    abrirModal("modalGasto");
}

document.addEventListener("click", function (e) {
    const btnEditar = e.target.closest(".js-editar-gasto");
    if (btnEditar) {
        const d = btnEditar.dataset;
        editarGasto(d.id, d.idNegocio, d.idCategoria, d.descripcion, d.proveedor, d.total, d.fecha, d.tipoComprobante, d.tipoPago, d.notas);
        return;
    }

    const btnHistorial = e.target.closest(".js-ver-historial-gasto");
    if (btnHistorial) { verHistorial(parseInt(btnHistorial.dataset.id)); return; }

    const btnEliminar = e.target.closest(".js-confirmar-eliminar-gasto");
    if (btnEliminar) {
        const el = document.getElementById("gastoNombreEliminar");
        if (el) el.innerHTML = `¿Seguro que deseas eliminar?<br><span>${btnEliminar.dataset.descripcion}</span>`;
        _eliminarGasto.confirmar(`/gastos/eliminar/${btnEliminar.dataset.id}`, btnEliminar.closest("tr"));
        return;
    }

    const btnEjecutar = e.target.closest(".js-ejecutar-eliminar-gasto");
    if (btnEjecutar) { ejecutarEliminarGasto(); return; }
});


function verHistorial(id) {
    abrirHistorial(
        `/gastos/${id}/historial`,
        "modalHistorial",
        "#tablaHistorial",
        h => renderDiff(h, "Gasto")
    );
}


// ── Gestión de categorías ────────────────────────────────────────────────────

const btnGestionarCats = document.getElementById("btn-gestionar-categorias");
if (btnGestionarCats) {
    btnGestionarCats.addEventListener("click", () => abrirModal("modalCategorias"));
}

async function recargarListaCategorias() {
    const wrap = document.getElementById("categorias-lista-wrap");
    if (!wrap) return;
    const res  = await fetch("/gastos/categorias/lista");
    wrap.innerHTML = await res.text();
}

function mostrarFeedbackCat(msg, tipo = "error") {
    const el = document.getElementById("cat-feedback");
    if (!el) return;
    el.textContent = msg;
    el.className   = `cat-feedback cat-feedback--${tipo}`;
    el.hidden      = false;
    setTimeout(() => { el.hidden = true; }, 4000);
}

async function enviarCategoria(id, nombre) {
    const body = { nombre };
    if (id) body.id_categoria = id;
    const res = await csrfFetch("/gastos/categorias/guardar", {
        method: "POST",
        body: JSON.stringify(body),
    });
    return res.json();
}

document.getElementById("btn-agregar-cat")?.addEventListener("click", async () => {
    const input = document.getElementById("nueva-cat-nombre");
    const nombre = input?.value.trim();
    if (!nombre) { mostrarFeedbackCat("Escribe el nombre de la categoría."); return; }
    const data = await enviarCategoria(null, nombre);
    if (data.ok) {
        input.value = "";
        mostrarFeedbackCat("Categoría agregada.", "ok");
        await recargarListaCategorias();
    } else {
        mostrarFeedbackCat(data.mensaje || "Error al agregar.");
    }
});

document.addEventListener("click", async function (e) {

    const btnEditarCat = e.target.closest(".js-editar-cat");
    if (btnEditarCat) {
        const id     = btnEditarCat.dataset.id;
        const nombre = btnEditarCat.dataset.nombre;
        const item   = btnEditarCat.closest(".cat-item");
        if (!item || item.classList.contains("editando")) return;

        item.classList.add("editando");
        const nombreEl = item.querySelector(".cat-nombre");
        const accsEl   = item.querySelector(".cat-acciones");

        const originalNombre = nombreEl.textContent;
        nombreEl.innerHTML = `<input class="cat-edit-input" value="${originalNombre}" maxlength="100">`;

        accsEl.innerHTML = `
            <button class="btn btn--primary btn--sm js-guardar-cat" data-id="${id}">Guardar</button>
            <button class="btn btn--secondary btn--sm js-cancelar-cat">Cancelar</button>
        `;
        item.querySelector(".cat-edit-input")?.focus();
        return;
    }

    const btnGuardarCat = e.target.closest(".js-guardar-cat");
    if (btnGuardarCat) {
        const id    = btnGuardarCat.dataset.id;
        const item  = btnGuardarCat.closest(".cat-item");
        const input = item?.querySelector(".cat-edit-input");
        const nombre = input?.value.trim();
        if (!nombre) { mostrarFeedbackCat("El nombre no puede estar vacío."); return; }
        const data = await enviarCategoria(id, nombre);
        if (data.ok) {
            mostrarFeedbackCat("Categoría actualizada.", "ok");
            await recargarListaCategorias();
        } else {
            mostrarFeedbackCat(data.mensaje || "Error al guardar.");
        }
        return;
    }

    const btnCancelarCat = e.target.closest(".js-cancelar-cat");
    if (btnCancelarCat) {
        await recargarListaCategorias();
        return;
    }

    const btnEliminarCat = e.target.closest(".js-eliminar-cat");
    if (btnEliminarCat) {
        const id     = btnEliminarCat.dataset.id;
        const nombre = btnEliminarCat.dataset.nombre;
        if (!confirm(`¿Eliminar la categoría "${nombre}"?`)) return;

        const res  = await csrfFetch(`/gastos/categorias/eliminar/${id}`, { method: "POST" });
        const data = await res.json();
        if (data.ok) {
            mostrarFeedbackCat("Categoría eliminada.", "ok");
            await recargarListaCategorias();
        } else {
            mostrarFeedbackCat(data.mensaje || "Error al eliminar.");
        }
        return;
    }
});
