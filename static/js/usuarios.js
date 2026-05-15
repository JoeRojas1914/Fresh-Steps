(function () {
    const input         = document.getElementById("buscar-input");
    const toggleInact   = document.getElementById("toggle-inactivos");
    const tbody         = document.querySelector("tbody");

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



window.abrirModalUsuario = function () {
    abrirModal("modalUsuario");

    document.getElementById("modalTitulo").innerText = "Agregar usuario";
    document.getElementById("id_usuario").value  = "";
    document.getElementById("usuario").value     = "";
    document.getElementById("password").value    = "";
    document.getElementById("pin").value         = "";
    document.getElementById("u_nombre").value    = "";
    document.getElementById("u_apellido").value  = "";
    document.getElementById("u_telefono").value  = "";
    document.getElementById("u_correo").value    = "";
    document.getElementById("u_cp").value        = "";
    document.getElementById("u_rol").value       = "caja";

    document.getElementById("password").required = true;
    document.getElementById("pin").required      = true;
    document.getElementById("pass-requerido").style.display = "";
    document.getElementById("pass-opcional").style.display  = "none";
    document.getElementById("pin-requerido").style.display  = "";
};


window.editarUsuario = function (e, u) {
    e.stopPropagation();
    abrirModal("modalUsuario");

    document.getElementById("modalTitulo").innerText = "Editar usuario";
    document.getElementById("id_usuario").value  = u.id_usuario;
    document.getElementById("usuario").value     = u.usuario     || "";
    document.getElementById("u_nombre").value    = u.nombre      || "";
    document.getElementById("u_apellido").value  = u.apellido    || "";
    document.getElementById("u_telefono").value  = u.telefono    || "";
    document.getElementById("u_correo").value    = u.correo      || "";
    document.getElementById("u_cp").value        = u.cp          || "";
    document.getElementById("u_rol").value       = u.rol         || "caja";
    document.getElementById("password").value    = "";
    document.getElementById("pin").value         = "";

    document.getElementById("password").required = false;
    document.getElementById("pin").required      = false;
    document.getElementById("pass-requerido").style.display = "none";
    document.getElementById("pass-opcional").style.display  = "";
    document.getElementById("pin-requerido").style.display  = "none";
};


document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("#formUsuario");
    if (!form) return;

    form.addEventListener("submit", function (e) {
        const creando  = !document.getElementById("id_usuario").value;
        const password = document.getElementById("password").value.trim();
        const pin      = document.getElementById("pin").value.trim();
        const username = document.getElementById("usuario").value.trim();
        const telefono = document.getElementById("u_telefono").value.trim();

        if (creando && !password) {
            alert("La contraseña es obligatoria al crear un usuario.");
            e.preventDefault(); return;
        }

        if (password && !/^(?=.*\d).{6,}$/.test(password)) {
            alert("La contraseña debe tener mínimo 6 caracteres y al menos 1 número.");
            e.preventDefault(); return;
        }

        if (creando && !/^\d{4}$/.test(pin)) {
            alert("El PIN debe tener exactamente 4 dígitos.");
            e.preventDefault(); return;
        }

        if (!/^[a-zA-Z0-9_]{3,}$/.test(username)) {
            alert("El usuario debe tener mínimo 3 caracteres (letras, números o _).");
            e.preventDefault(); return;
        }

        if (telefono && !/^\d{10}$/.test(telefono)) {
            alert("El teléfono debe tener exactamente 10 dígitos.");
            e.preventDefault(); return;
        }
    });
});


window.verHistorialUsuario = async function (e, id) {
    e.stopPropagation();
    abrirModal("modalHistorialUsuario");

    const tbody = document.querySelector("#tablaHistorialUsuario tbody");
    tbody.innerHTML = "<tr><td colspan='4'>Cargando...</td></tr>";

    try {
    const res  = await fetch(`/usuarios/${id}/historial`);
    if (!res.ok) throw new Error("Error de red");
    const data = await res.json();

    if (!data.length) {
        tbody.innerHTML = "<tr><td colspan='4' style='text-align:center;opacity:.5;'>Sin historial</td></tr>";
        return;
    }

    tbody.innerHTML = data.map(h => `
        <tr>
            <td><strong>${escapeHtml(h.accion)}</strong></td>
            <td>${escapeHtml(h.usuario_admin || "—")}</td>
            <td>${new Date(h.fecha).toLocaleString("es-MX")}</td>
            <td>${_detalleHistorial(h)}</td>
        </tr>
    `).join("");
    } catch {
        tbody.innerHTML = "<tr><td colspan='4' style='text-align:center;opacity:.5;'>Error al cargar historial.</td></tr>";
    }
};

function _detalleHistorial(h) {
    if (h.accion === "CREADO")       return "Usuario creado";
    if (h.accion === "TOGGLE_ACTIVO") {
        try {
            const d = JSON.parse(h.datos_despues);
            return d.activo ? "Activado" : "Desactivado";
        } catch { return "Cambio de estado"; }
    }
    if (h.accion === "EDITADO") {
        try {
            const a = JSON.parse(h.datos_antes  || "{}");
            const d = JSON.parse(h.datos_despues || "{}");
            const cambios = [];
            const campos = ["usuario","rol","nombre","apellido","telefono","correo","cp"];
            campos.forEach(c => {
                if ((a[c] || "") !== (d[c] || ""))
                    cambios.push(`${escapeHtml(c)}: <em>${escapeHtml(a[c] || "—")}</em> → <strong>${escapeHtml(d[c] || "—")}</strong>`);
            });
            return cambios.length ? cambios.join(" | ") : "Sin cambios visibles";
        } catch { return "Editado"; }
    }
    return h.accion;
}