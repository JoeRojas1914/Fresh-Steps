document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector(".modal-form");
    if (form) {
        form.addEventListener("submit", function (e) {
            const negocio = document.getElementById("id_negocio").value;
            const nombre = document.querySelector("[name=nombre]").value.trim();
            const precio = document.querySelector("[name=precio]").value;

            if (!negocio || !nombre || precio === "") {
                alert("Negocio, nombre y precio son obligatorios.");
                e.preventDefault();
                return;
            }

            if (parseFloat(precio) < 0) {
                alert("El precio no puede ser negativo.");
                e.preventDefault();
            }
        });
    }

    const select = document.getElementById("select-negocio-servicios");
    const toggle = document.getElementById("toggle-eliminados-servicios");
    const formFiltro = document.getElementById("form-filtro-servicios");

    if (formFiltro) {
        if (select) {
            select.addEventListener("change", () => formFiltro.submit());
        }

        if (toggle) {
            toggle.addEventListener("change", () => formFiltro.submit());
        }
    }
});


window.abrirNuevoServicio = function () {
    abrirModal("modalServicio");

    document.getElementById("modalServicio_title").innerText = "Agregar servicio";
    document.getElementById("id_servicio").value = "";

    document.querySelector(".modal-form").reset();
};


window.editarServicio = function (btn) {
    abrirModal("modalServicio");

    document.getElementById("modalServicio_title").innerText = "Editar servicio";

    document.getElementById("id_servicio").value = btn.dataset.id;
    document.getElementById("id_negocio").value = btn.dataset.negocio;
    document.querySelector("[name=nombre]").value = btn.dataset.nombre;
    document.querySelector("[name=precio]").value = btn.dataset.precio;
};


window.verHistorialServicio = async function (id) {

    abrirModal("modalHistorialServicio");

    const tbody = document.getElementById("tablaHistorialServicio");

    tbody.innerHTML = "<tr><td colspan='4'>Cargando...</td></tr>";

    try {
    const res = await fetch(`/servicios/${id}/historial`);
    if (!res.ok) throw new Error("Error de red");
    const data = await res.json();

    if (!data.length) {
        tbody.innerHTML = "<tr><td colspan='4'>Sin historial</td></tr>";
        return;
    }

    tbody.innerHTML = "";

    data.forEach(h => {

        const antes = h.datos_antes ? JSON.parse(h.datos_antes) : null;
        const despues = h.datos_despues ? JSON.parse(h.datos_despues) : null;

        let cambios = "";

        if (h.accion === "CREADO") {
            cambios = "Servicio creado";
        }
        else if (h.accion === "EDITADO" && antes && despues) {
            Object.keys(despues).forEach(k => {
                if (antes[k] !== despues[k]) {
                    cambios += `
                        <div>
                            <b>${escapeHtml(k)}</b>:
                            <span style="color:#ef4444">${escapeHtml(antes[k])}</span>
                            →
                            <span style="color:#22c55e">${escapeHtml(despues[k])}</span>
                        </div>
                    `;
                }
            });
        }
        else if (h.accion === "ELIMINADO") {
            cambios = "Servicio eliminado";
        }
        else if (h.accion === "RESTAURADO") {
            cambios = "Servicio restaurado";
        }

        tbody.innerHTML += `
            <tr>
                <td><b>${escapeHtml(h.accion)}</b></td>
                <td>${escapeHtml(h.usuario)}</td>
                <td>${new Date(h.fecha).toLocaleString()}</td>
                <td>${cambios}</td>
            </tr>
        `;
    });
    } catch {
        tbody.innerHTML = "<tr><td colspan='4'>Error al cargar historial.</td></tr>";
    }
};