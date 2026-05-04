document.addEventListener("DOMContentLoaded", () => {

    const form = document.querySelector(".modal-form");
    if (!form) return;

    form.addEventListener("submit", function (e) {
        const nombre = document.querySelector("[name=nombre]").value.trim();
        const apellido = document.querySelector("[name=apellido]").value.trim();
        const telefono = document.querySelector("[name=telefono]").value.trim();

        if (!nombre || !apellido || !telefono) {
            alert("Nombre, apellido y teléfono son obligatorios.");
            e.preventDefault();
            return;
        }

        if (!/^\d{10}$/.test(telefono)) {
            alert("El teléfono debe tener exactamente 10 dígitos.");
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

  const res = await fetch(`/clientes/${id}/historial`);
  const data = await res.json();

  if (!data.length) {
    tbody.innerHTML = "<tr><td colspan='4'>Sin historial</td></tr>";
    return;
  }

  tbody.innerHTML = "";
  data.forEach(h => {
    tbody.innerHTML += `
      <tr>
        <td><b>${h.accion}</b></td>
        <td>${h.usuario}</td>
        <td>${new Date(h.fecha).toLocaleString()}</td>
        <td>${h.datos_despues ? "Modificación" : h.accion}</td>
      </tr>
    `;
  });
};


window.confirmarEliminarCliente = function (idCliente) {
    if (!confirm("¿Seguro que desea desactivar al cliente?")) return;
    window.location.href = `/clientes/eliminar/${idCliente}`;
};

window.restaurarCliente = function (idCliente) {
    window.location.href = `/clientes/restaurar/${idCliente}`;
};

document.addEventListener("click", function (e) {
    const row = e.target.closest("tr[data-href]");
    if (!row) return;

    if (e.target.closest(".no-row-click")) return;

    window.location.href = row.dataset.href;
});


(function () {
    const input = document.getElementById("buscar-cliente-input");
    if (!input) return;

    const filas = document.querySelectorAll(".table tbody tr");

    function normalizar(txt) {
        return txt.toLowerCase()
            .normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim();
    }

    input.addEventListener("input", () => {
        const q = normalizar(input.value);
        filas.forEach(fila => {
            const nombre = normalizar(fila.querySelector("td")?.innerText || "");
            fila.style.display = nombre.includes(q) ? "" : "none";
        });
    });
}());