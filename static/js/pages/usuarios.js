import { abrirModal, cerrarModal } from '../components/modal.js';
import { initModalForm, mostrarFeedback, escapeHtml, apiAction, csrfFetch, recargarConFeedback } from '../base/helpers.js';
import { validarRequerido, validarTelefono, validarPassword, validarPin, validarUsername } from '../base/form_validators.js';
import { abrirHistorial } from '../base/historial_helpers.js';

(function () {
    const input       = document.getElementById("buscar-input");
    const toggleInact = document.getElementById("toggle-inactivos");

    if (input) {
        let debounceTimer;
        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const url = new URL(window.location.href);
                const q = input.value.trim();
                url.searchParams.delete("pagina");
                if (q) url.searchParams.set("q", q);
                else   url.searchParams.delete("q");
                window.location.href = url.toString();
            }, 500);
        });
    }

    if (toggleInact) {
        toggleInact.addEventListener("change", () => {
            const url = new URL(window.location.href);
            url.searchParams.delete("pagina");
            if (toggleInact.checked) url.searchParams.set("inactivos", "1");
            else                     url.searchParams.delete("inactivos");
            window.location.href = url.toString();
        });
    }
}());



let _pendingToggleUrl = null;

function confirmarToggleUsuario(id, accion) {
    _pendingToggleUrl = `/usuarios/toggle/${id}`;
    document.getElementById("modalToggleTitulo").innerText  = `${accion} usuario`;
    document.getElementById("modalToggleMensaje").innerText = `¿Seguro que deseas ${accion.toLowerCase()} este usuario?`;
    abrirModal("modalConfirmarToggleUsuario");
}

function ejecutarToggleUsuario() {
    if (!_pendingToggleUrl) return;
    const url = _pendingToggleUrl;
    _pendingToggleUrl = null;
    apiAction({
        url,
        msgError: "No se pudo cambiar el estado del usuario.",
        reload: true,
        reloadDelay: 300,
    });
}


function abrirModalUsuario() {
    document.getElementById("modalTitulo").innerText  = "Agregar usuario";
    document.getElementById("id_usuario").value       = "";
    document.getElementById("usuario").value          = "";
    document.getElementById("password").value         = "";
    document.getElementById("pin").value              = "";
    document.getElementById("u_nombre").value         = "";
    document.getElementById("u_apellido").value       = "";
    document.getElementById("u_telefono").value       = "";
    document.getElementById("u_correo").value         = "";
    document.getElementById("u_cp").value             = "";
    document.getElementById("u_rol").value            = "caja";

    document.getElementById("password").required            = true;
    document.getElementById("pin").required                 = true;
    document.getElementById("pass-requerido").style.display = "inline";
    document.getElementById("pass-opcional").style.display  = "none";
    document.getElementById("pin-requerido").style.display  = "inline";

    abrirModal("modalUsuario");
}


function editarUsuario(e, btn) {
    e.stopPropagation();
    const d = btn.dataset;

    document.getElementById("modalTitulo").innerText = "Editar usuario";
    document.getElementById("id_usuario").value      = d.id;
    document.getElementById("usuario").value         = d.usuario   || "";
    document.getElementById("u_nombre").value        = d.nombre    || "";
    document.getElementById("u_apellido").value      = d.apellido  || "";
    document.getElementById("u_telefono").value      = d.telefono  || "";
    document.getElementById("u_correo").value        = d.correo    || "";
    document.getElementById("u_cp").value            = d.cp        || "";
    document.getElementById("u_rol").value           = d.rol       || "caja";
    document.getElementById("password").value        = "";
    document.getElementById("pin").value             = "";

    document.getElementById("password").required            = false;
    document.getElementById("pin").required                 = false;
    document.getElementById("pass-requerido").style.display = "none";
    document.getElementById("pass-opcional").style.display  = "inline";
    document.getElementById("pin-requerido").style.display  = "none";

    abrirModal("modalUsuario");
}


document.addEventListener("DOMContentLoaded", () => {
    const form      = document.getElementById("formUsuario");
    const submitBtn = form?.querySelector('[type="submit"]');
    const modalEl   = document.getElementById("modalUsuario");

    let revalidate = () => {};
    if (form && submitBtn) {
        revalidate = initModalForm(form, submitBtn);
        modalEl?.addEventListener("modal:opened", () => revalidate());
    }

    if (!form) return;

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const creando  = !document.getElementById("id_usuario").value;
        const password = document.getElementById("password").value.trim();
        const pin      = document.getElementById("pin").value.trim();
        const username = document.getElementById("usuario").value.trim();
        const telefono = document.getElementById("u_telefono").value.trim();

        if (creando && !validarRequerido(password)) {
            mostrarFeedback("La contraseña es obligatoria al crear un usuario.", "error");
            return;
        }
        if (password && !validarPassword(password)) {
            mostrarFeedback("La contraseña debe tener mínimo 6 caracteres y al menos 1 número.", "error");
            return;
        }
        if (creando && !validarPin(pin)) {
            mostrarFeedback("El PIN debe tener entre 4 y 6 dígitos numéricos.", "error");
            return;
        }
        if (!validarUsername(username)) {
            mostrarFeedback("El usuario debe tener mínimo 3 caracteres (letras, números o _).", "error");
            return;
        }
        if (telefono && !validarTelefono(telefono)) {
            mostrarFeedback("El teléfono debe tener exactamente 10 dígitos.", "error");
            return;
        }

        const btn = form.querySelector('[type="submit"]');
        const textoOriginal = btn ? btn.textContent : "";
        if (btn) { btn.disabled = true; btn.textContent = "Guardando..."; }

        try {
            const r = await csrfFetch("/usuarios/guardar", {
                method: "POST",
                body: JSON.stringify({
                    id_usuario: document.getElementById("id_usuario").value,
                    usuario:    username,
                    password:   password,
                    pin:        pin,
                    nombre:     document.getElementById("u_nombre").value.trim(),
                    apellido:   document.getElementById("u_apellido").value.trim(),
                    telefono:   telefono,
                    correo:     document.getElementById("u_correo").value.trim(),
                    cp:         document.getElementById("u_cp").value.trim(),
                    rol:        document.getElementById("u_rol").value,
                })
            });
            const res = await r.json();
            if (res.ok) {
                cerrarModal("modalUsuario");
                recargarConFeedback(res.message || "Usuario guardado correctamente.");
            } else {
                mostrarFeedback(res.error || "Error al guardar el usuario.", "error");
                if (btn) { btn.disabled = false; btn.textContent = textoOriginal; }
            }
        } catch {
            mostrarFeedback("Error de conexión. Intenta de nuevo.", "error");
            if (btn) { btn.disabled = false; btn.textContent = textoOriginal; }
        }
    });
});


document.addEventListener("click", function (e) {
    const btnAbrir = e.target.closest(".js-abrir-modal-usuario");
    if (btnAbrir) { abrirModalUsuario(); return; }

    const btnEditar = e.target.closest(".js-editar-usuario");
    if (btnEditar) { editarUsuario(e, btnEditar); return; }

    const btnToggle = e.target.closest(".js-confirmar-toggle");
    if (btnToggle) { confirmarToggleUsuario(parseInt(btnToggle.dataset.id), btnToggle.dataset.accion); return; }

    const btnHistorial = e.target.closest(".js-ver-historial-usuario");
    if (btnHistorial) { e.stopPropagation(); verHistorialUsuario(e, parseInt(btnHistorial.dataset.id)); return; }

    const btnEjecutar = e.target.closest(".js-ejecutar-toggle-usuario");
    if (btnEjecutar) { ejecutarToggleUsuario(); return; }
});

function verHistorialUsuario(e, id) {
    e.stopPropagation();
    abrirHistorial(
        `/usuarios/${id}/historial`,
        "modalHistorialUsuario",
        "#tablaHistorialUsuario tbody",
        _detalleHistorialUsuario
    );
}

function _detalleHistorialUsuario(h) {
    if (h.accion === "CREADO") return "Usuario creado";
    if (h.accion === "TOGGLE_ACTIVO") {
        try {
            const d = JSON.parse(h.datos_despues);
            return d.activo ? "Activado" : "Desactivado";
        } catch { return "Cambio de estado"; }
    }
    if (h.accion === "EDITADO") {
        try {
            const a = JSON.parse(h.datos_antes   || "{}");
            const d = JSON.parse(h.datos_despues || "{}");
            const campos = ["usuario", "rol", "nombre", "apellido", "telefono", "correo", "cp"];
            const cambios = campos
                .filter(c => (a[c] || "") !== (d[c] || ""))
                .map(c => `${escapeHtml(c)}: <em>${escapeHtml(a[c] || "—")}</em> → <strong>${escapeHtml(d[c] || "—")}</strong>`);
            return cambios.length ? cambios.join(" | ") : "Sin cambios visibles";
        } catch { return "Editado"; }
    }
    return escapeHtml(h.accion);
}
