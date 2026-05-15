const detallesCargados = {};

function toggleDetalles(idVenta) {
    const fila = document.getElementById(`detalles-${idVenta}`);
    const lista = document.getElementById(`lista-detalles-${idVenta}`);

    if (!fila || !lista) return;

    const visible = fila.style.display === "table-row";

    if (visible) {
        fila.style.display = "none";
        return;
    }

    fila.style.display = "table-row";

    if (detallesCargados[idVenta]) return;

    lista.innerHTML = `<li style="opacity:0.6;">Cargando...</li>`;

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
                            👟 ${escapeHtml(item.datos.tipo)} ${escapeHtml(item.datos.marca)}
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
                            🧵 ${escapeHtml(item.datos.tipo)} ${escapeHtml(item.datos.marca)}
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
                            🏭 ${escapeHtml(item.datos.tipo)}
                        </div>
                        <div>
                            Cantidad: <b>${escapeHtml(item.datos.cantidad)}</b> |
                            Precio: <b>$${parseFloat(item.datos.precio_unitario).toFixed(2)}</b>
                        </div>
                    `;
                }

                if (item.comentario) {
                    html += `
                        <div style="margin-top:6px; font-style:italic; opacity:0.8;">
                            💬 ${escapeHtml(item.comentario)}
                        </div>
                    `;
                }

                return `<li class="detalle-item">${html}</li>`;
            }).join("");
        })
        .catch(() => {
            lista.innerHTML = `<li>Error al cargar detalles</li>`;
        });
}