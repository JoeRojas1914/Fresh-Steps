document.addEventListener("DOMContentLoaded", () => {

    const form = document.querySelector(".modal-form");

    if (form) form.addEventListener("submit", function (e) {
        const nombre = document.querySelector("[name=nombre]").value.trim();
        const apellido = document.querySelector("[name=apellido]").value.trim();
        const telefono = document.querySelector("[name=telefono]").value.trim();

        if (!nombre || !apellido || !telefono) {
            mostrarFeedback("Nombre, apellido y teléfono son obligatorios.", "error");
            e.preventDefault();
            return;
        }

        if (!/^\d{10}$/.test(telefono)) {
            mostrarFeedback("El teléfono debe tener exactamente 10 dígitos.", "error");
            e.preventDefault();
        }
    });

});


window.editarClienteBtn = function (e, btn) {
  e.stopPropagation();

  const modal = document.getElementById("modalCliente");

  abrirModal("modalCliente");

  modal.querySelector(".modal__title").innerText = "Editar cliente";

  modal.querySelector("#id_cliente").value = btn.dataset.id;

  modal.querySelector("[name=nombre]").value = btn.dataset.nombre;
  modal.querySelector("[name=apellido]").value = btn.dataset.apellido;
  modal.querySelector("[name=correo]").value = btn.dataset.correo || "";
  modal.querySelector("[name=telefono]").value = btn.dataset.telefono;
  modal.querySelector("[name=direccion]").value = btn.dataset.direccion || "";
};



window.cerrarHistorialCliente = function () {
    document.getElementById("modalHistorialCliente").style.display = "none";
};

window.verHistorialCliente = async function (e, id) {
  e.stopPropagation();

  const tbody = document.querySelector("#tablaHistorialCliente tbody");
  tbody.innerHTML = "<tr><td colspan='4'>Cargando...</td></tr>";

  abrirModal("modalHistorialCliente");

  try {
    const res = await fetch(`/clientes/${id}/historial`);
    if (!res.ok) throw new Error("Error de red");
    const data = await res.json();

    if (!data.length) {
      tbody.innerHTML = "<tr><td colspan='4'>Sin historial</td></tr>";
      return;
    }

    tbody.innerHTML = "";
    data.forEach(h => {
      tbody.innerHTML += `
        <tr>
          <td><b>${escapeHtml(h.accion)}</b></td>
          <td>${escapeHtml(h.usuario)}</td>
          <td>${new Date(h.fecha).toLocaleString()}</td>
          <td>${h.datos_despues ? "Modificación" : escapeHtml(h.accion)}</td>
        </tr>
      `;
    });
  } catch {
    tbody.innerHTML = "<tr><td colspan='4'>Error al cargar historial.</td></tr>";
  }
};


window.confirmarEliminarCliente = function (idCliente) {
    if (!confirm("¿Seguro que desea desactivar al cliente?")) return;
    window.location.href = `/clientes/eliminar/${idCliente}`;
};

window.restaurarCliente = function (idCliente) {
    window.location.href = `/clientes/restaurar/${idCliente}`;
};

document.addEventListener("click", function (e) {
    if (e.target.closest(".modal")) return;

    const row = e.target.closest("tr[data-href]");
    if (!row) return;

    if (e.target.closest(".no-row-click")) return;
    if (e.target.tagName === "BUTTON" || e.target.tagName === "A") return;

    window.location.href = row.dataset.href;
});


(function () {
    const input = document.getElementById("buscar-cliente-input");
    if (!input) return;

    let debounceTimer;
    input.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            const url = new URL(window.location.href);
            const q = input.value.trim();
            if (q) {
                url.searchParams.set("q", q);
            } else {
                url.searchParams.delete("q");
            }
            url.searchParams.delete("pagina");
            window.location.href = url.toString();
        }, 400);
    });
}());

(function () {
    const toggle = document.getElementById("toggle-eliminados");
    if (!toggle) return;

    toggle.addEventListener("change", () => {
        const url = new URL(window.location.href);
        if (toggle.checked) {
            url.searchParams.set("eliminados", "1");
        } else {
            url.searchParams.delete("eliminados");
        }
        url.searchParams.delete("pagina");
        window.location.href = url.toString();
    });
}());