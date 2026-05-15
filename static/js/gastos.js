document.addEventListener("DOMContentLoaded", () => {

    const form = document.querySelector(".modal-form");
    if (!form) return;

    form.addEventListener("submit", function (e) {
        const descripcion = document.querySelector("[name=descripcion]").value.trim();
        const proveedor = document.querySelector("[name=proveedor]").value.trim();
        const total = document.querySelector("[name=total]").value;

        if (!descripcion || !proveedor || total === "") {
            alert("Descripción, proveedor y total son obligatorios.");
            e.preventDefault();
            return;
        }

        if (parseFloat(total) < 0) {
            alert("El total no puede ser negativo.");
            e.preventDefault();
        }
    });

});


window.editarGasto = function (
    id,
    id_negocio,
    descripcion,
    proveedor,
    total,
    fecha_registro,
    tipo_comprobante,
    tipo_pago
) {
    abrirModal("modalGasto");

    document.getElementById("modalGasto_title").innerText = "Editar gasto";

    document.getElementById("id_gasto").value = id;
    document.getElementById("id_negocio").value = id_negocio;
    document.querySelector("[name=descripcion]").value = descripcion;
    document.querySelector("[name=proveedor]").value = proveedor;
    document.querySelector("[name=total]").value = total;
    document.querySelector("[name=fecha_registro]").value = fecha_registro || "";
    document.getElementById("tipo_comprobante").value = tipo_comprobante;
    document.getElementById("tipo_pago").value = tipo_pago;
};




window.verHistorial = async function (id) {

    const modal = document.getElementById("modalHistorial");
    const tbody = document.getElementById("tablaHistorial");

    tbody.innerHTML = "<tr><td colspan='4'>Cargando...</td></tr>";
    abrirModal("modalHistorial");

    try {
    const res = await fetch(`/gastos/${id}/historial`);
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

        if (h.accion === "RESTAURADO") {
            cambios = "<span>Registro restaurado</span>";
        }
        else if (antes && despues) {
            Object.keys(despues).forEach(k => {
                if (antes[k] !== despues[k]) {
                    cambios += `
                        <div>
                            <b>${k}</b>:
                            <span style="color:#ef4444">${antes[k]}</span>
                            →
                            <span style="color:#22c55e">${despues[k]}</span>
                        </div>
                    `;
                }
            });
        }
        else if (despues) {
            cambios = "Registro creado";
        }
        else {
            cambios = "Registro eliminado";
        }

        tbody.innerHTML += `
            <tr>
                <td><b>${h.accion}</b></td>
                <td>${h.usuario}</td>
                <td>${new Date(h.fecha).toLocaleString()}</td>
                <td>${cambios}</td>
            </tr>
        `;
    });
    } catch {
        tbody.innerHTML = "<tr><td colspan='4'>Error al cargar historial.</td></tr>";
    }
};
