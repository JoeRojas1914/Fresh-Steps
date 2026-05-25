import { escapeHtml } from '../base/helpers.js';

const detallesCargados = {};

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".btn-detalles[data-id]").forEach(function (btn) {
        btn.addEventListener("click", function () { toggleDetalles(btn.dataset.id, btn); });
    });
});

document.addEventListener("click", function (e) {
    const btn = e.target.closest(".js-ver-ticket");
    if (btn) { window.open(btn.dataset.url, "_blank"); }
});

export function toggleDetalles(idVenta, btn) {
    const fila  = document.getElementById(`detalles-${idVenta}`);
    const lista = document.getElementById(`lista-detalles-${idVenta}`);

    if (!fila || !lista) return;

    const visible = fila.style.display === "table-row";
    const chevron = btn ? btn.querySelector(".chevron-icon") : null;

    if (visible) {
        const box = fila.querySelector(".detalles-box");
        if (chevron) chevron.style.transform = "";
        if (box) {
            box.classList.add("detalles-box--closing");
            box.addEventListener("animationend", () => {
                fila.style.display = "none";
                box.classList.remove("detalles-box--closing");
            }, { once: true });
        } else {
            fila.style.display = "none";
        }
        return;
    }

    fila.style.display = "table-row";
    if (chevron) chevron.style.transform = "rotate(180deg)";

    if (detallesCargados[idVenta]) return;

    lista.innerHTML = `<li class="dim-soft">Cargando...</li>`;

    fetch(`/ventas/detalles/${idVenta}`)
        .then(r => r.json())
        .then(detalles => {

            detallesCargados[idVenta] = true;

            if (!detalles.length) {
                lista.innerHTML = `<li>Sin detalles</li>`;
                return;
            }

            lista.innerHTML = detalles.map(item => {

                let html = "";

                if (item.tipo_articulo === "calzado") {
                    html += `
                        <div class="detalle-zapato">
                            <i data-lucide="footprints" width="14" height="14"></i>
                            ${escapeHtml(item.datos.tipo)} ${escapeHtml(item.datos.marca)}
                        </div>
                    `;

                    html += item.servicios.map(s => `
                        <div class="detalle-servicio">
                            ${escapeHtml(s.nombre)}
                            <span class="detalle-precio">
                                $${parseFloat(s.precio_aplicado).toFixed(2)}
                            </span>
                        </div>
                    `).join("");
                }

                else if (item.tipo_articulo === "confeccion") {
                    html += `
                        <div class="detalle-zapato">
                            <i data-lucide="scissors" width="14" height="14"></i>
                            ${escapeHtml(item.datos.tipo)} ${escapeHtml(item.datos.marca)}
                        </div>
                        <div>
                            Cantidad: <b>${escapeHtml(item.datos.cantidad)}</b>
                        </div>
                    `;

                    html += item.servicios.map(s => `
                        <div class="detalle-servicio">
                            ${escapeHtml(s.nombre)}
                            <span class="detalle-precio">
                                $${parseFloat(s.precio_aplicado).toFixed(2)}
                            </span>
                        </div>
                    `).join("");
                }

                else if (item.tipo_articulo === "maquila") {
                    html += `
                        <div class="detalle-zapato">
                            <i data-lucide="factory" width="14" height="14"></i>
                            ${escapeHtml(item.datos.tipo)}
                        </div>
                        <div>
                            Cantidad: <b>${escapeHtml(item.datos.cantidad)}</b> |
                            Precio: <b>$${parseFloat(item.datos.precio_unitario).toFixed(2)}</b>
                        </div>
                    `;
                }

                if (item.comentario) {
                    html += `
                        <div class="mt-6 dim-mid nota-italic">
                            <i data-lucide="message-circle" width="13" height="13"></i>
                            ${escapeHtml(item.comentario)}
                        </div>
                    `;
                }

                return `<li class="detalle-item">${html}</li>`;
            }).join("");
            if (window.lucide) lucide.createIcons();
        })
        .catch(() => {
            lista.innerHTML = `<li>Error al cargar detalles</li>`;
        });
}
