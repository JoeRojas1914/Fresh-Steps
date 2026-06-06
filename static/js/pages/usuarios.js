import { abrirModal } from '../components/modal.js';
import { mostrarFeedback, normalizar, escapeHtml } from '../base/helpers.js';
import { validarRequerido, validarTelefono, validarPassword, validarPin, validarUsername } from '../base/form_validators.js';
import { abrirHistorial } from '../base/historial_helpers.js';

const _usuariosMap = (() => {
    const el = document.getElementById("usuariosData");
    if (!el) return {};
    try {
        const lista = JSON.parse(el.textContent);
        return Object.fromEntries(lista.map(u => [u.id_usuario, u]));
    } catch { return {}; }
})();

(function () {
    const input       = document.getElementById("buscar-input");
    const toggleInact = document.getElementById("toggle-inactivos");
    const tbody       = document.querySelector("tbody");

    if (!input) return;

    function aplicarFiltros() {
        const q            = normalizar(input.value);
        const verInactivos = toggleInact.checked;

        const filas = Array.from(document.querySelectorAll("tbody tr[data-id]"));

        filas.forEach(fila => {
            const texto  = normalizar(fila.dataset.buscar || "");
            const activo = fila.dataset.activo === "1";
            const esAdmin = fila.dataset.rol === "admin";

            const okQ      = !q || texto.includes(q);
            const okActivo = esAdmin || activo || verInactivos;

            fila.style.display = (okQ && okActivo) ? "" : "none";
        });

        const adminFila = filas.find(f => f.dataset.rol === "admin");
        if (adminFila && tbody) {
            tbody.prepend(adminFila);
        }
    }

    input.addEventListener("input", aplicarFiltros);
    toggleInact.addEventListener("change", aplicarFiltros);

    aplicarFiltros();
}());



let _pendingToggleUrl = null;

function confirmarToggleUsuario(id, accion) {
    _pendingToggleUrl = `/usuarios/toggle/${id}`;
    document.getElementById("modalToggleTitulo").innerText  = `${accion} usuario`;
    document.getElementById("modalToggleMensaje").innerText = `¿Seguro que deseas ${accion.toLowerCase()} este usuario?`;
    abrirModal("modalConfirmarToggleUsuario");
}

function ejecutarToggleUsuario() {
    if (_pendingToggleUrl) location.href = _pendingToggleUrl;
}


function abrirModalUsuario() {
    abrirModal("modalUsuario");

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

    document.getElementById("password").required                  = true;
    document.getElementById("pin").required                       = true;
    document.getElementById("pass-requerido").style.display       = "inline";
    document.getElementById("pass-opcional").style.display        = "none";
    document.getElementById("pin-requerido").style.display        = "inline";
}


function editarUsuario(e, u) {
    e.stopPropagation();
    abrirModal("modalUsuario");

    document.getElementById("modalTitulo").innerText = "Editar usuario";
    document.getElementById("id_usuario").value      = u.id_usuario;
    document.getElementById("usuario").value         = u.usuario     || "";
    document.getElementById("u_nombre").value        = u.nombre      || "";
    document.getElementById("u_apellido").value      = u.apellido    || "";
    document.getElementById("u_telefono").value      = u.telefono    || "";
    document.getElementById("u_correo").value        = u.correo      || "";
    document.getElementById("u_cp").value            = u.cp          || "";
    document.getElementById("u_rol").value           = u.rol         || "caja";
    document.getElementById("password").value        = "";
    document.getElementById("pin").value             = "";

    document.getElementById("password").required            = false;
    document.getElementById("pin").required                 = false;
    document.getElementById("pass-requerido").style.display = "none";
    document.getElementById("pass-opcional").style.display  = "inline";
    document.getElementById("pin-requerido").style.display  = "none";
}


document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("#formUsuario");
    if (!form) return;

    form.addEventListener("submit", function (e) {
        const creando  = !document.getElementById("id_usuario").value;
        const password = document.getElementById("password").value.trim();
        const pin      = document.getElementById("pin").value.trim();
        const username = document.getElementById("usuario").value.trim();
        const telefono = document.getElementById("u_telefono").value.trim();

        if (creando && !validarRequerido(password)) {
            mostrarFeedback("La contraseña es obligatoria al crear un usuario.", "error");
            e.preventDefault(); return;
        }

        if (password && !validarPassword(password)) {
            mostrarFeedback("La contraseña debe tener mínimo 6 caracteres y al menos 1 número.", "error");
            e.preventDefault(); return;
        }

        if (creando && !validarPin(pin)) {
            mostrarFeedback("El PIN debe tener entre 4 y 6 dígitos numéricos.", "error");
            e.preventDefault(); return;
        }

        if (!validarUsername(username)) {
            mostrarFeedback("El usuario debe tener mínimo 3 caracteres (letras, números o _).", "error");
            e.preventDefault(); return;
        }

        if (telefono && !validarTelefono(telefono)) {
            mostrarFeedback("El teléfono debe tener exactamente 10 dígitos.", "error");
            e.preventDefault(); return;
        }
    });
});


document.addEventListener("click", function (e) {
    const btnAbrir = e.target.closest(".js-abrir-modal-usuario");
    if (btnAbrir) { abrirModalUsuario(); return; }

    const btnEditar = e.target.closest(".js-editar-usuario");
    if (btnEditar) {
        e.stopPropagation();
        const u = _usuariosMap[parseInt(btnEditar.dataset.id)];
        if (u) editarUsuario(e, u);
        return;
    }

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
