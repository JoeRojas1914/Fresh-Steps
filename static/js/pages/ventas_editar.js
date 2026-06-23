import { ventaState } from './ventas_state.js';
import { mostrarFeedback, redirigirConFeedback, escapeHtml } from '../base/helpers.js';
import { abrirModal, cerrarModal } from '../components/modal.js';
import { initNavigationGuard } from '../base/navigation_guard.js';
import { cargarServicios, agregarServicio, eliminarServicioPro, onChangeServicio, marcarPrecioEditado } from './ventas_servicios.js';
import { agregarArticulo, eliminarArticulo, validarArticuloVisual } from './ventas_articulos.js';


function calcularDeltaNuevos() {
    const negocio = document.getElementById("id_negocio").value;
    let total = 0;

    if (negocio === "1") {
        document.querySelectorAll("#articulos-container .servicio-item").forEach(fila => {
            const sel    = fila.querySelector("select");
            const precio = fila.querySelector(".precio-aplicado");
            if (sel && sel.value) total += parseFloat(precio?.value || 0);
        });
    }

    if (negocio === "2") {
        document.querySelectorAll("#articulos-container .articulo-item").forEach(articulo => {
            const cantidad = parseFloat(articulo.querySelector("input[name$='[cantidad]']")?.value || 1);
            articulo.querySelectorAll(".servicio-item").forEach(fila => {
                const sel    = fila.querySelector("select");
                const precio = fila.querySelector(".precio-aplicado");
                if (sel && sel.value) total += cantidad * parseFloat(precio?.value || 0);
            });
        });
    }

    if (negocio === "3") {
        document.querySelectorAll("#articulos-container .articulo-item").forEach(item => {
            const cantidad = parseFloat(item.querySelector("input[name$='[cantidad]']")?.value || 0);
            const precio   = parseFloat(item.querySelector("input[name$='[precio_unitario]']")?.value || 0);
            total += cantidad * precio;
        });
    }

    return total;
}


function _artInput(scope, campo) {
    return [...scope.querySelectorAll("[name^='art_edit']")]
        .find(inp => inp.name.endsWith(`[${campo}]`));
}

function calcularDeltaExistentes() {
    let delta = 0;

    document.querySelectorAll(".servicio-ro-item").forEach(item => {
        const artItem  = item.closest(".articulo-item--readonly");
        if (!artItem) return;
        const tipo     = artItem.dataset.tipo;
        const cantidad = parseFloat(artItem.dataset.cantidad || 1);
        const mult     = tipo === "confeccion" ? cantidad : 1;

        const original = parseFloat(item.dataset.precioOriginal || 0);
        const deleted  = item.querySelector(".existing-delete-flag")?.value === "1";

        if (deleted) {
            delta -= original * mult;
        } else {
            const nuevo = parseFloat(item.querySelector(".servicio-ro-precio-input")?.value ?? original);
            delta += (nuevo - original) * mult;
        }
    });

    document.querySelectorAll(".agregar-servicios-existente").forEach(box => {
        const tipo     = box.dataset.tipo;
        const cantidad = parseFloat(box.dataset.cantidad || 1);
        box.querySelectorAll(".existing-servicio-item").forEach(fila => {
            const sel    = fila.querySelector("select");
            const precio = parseFloat(fila.querySelector(".precio-aplicado")?.value || 0);
            if (sel?.value && precio > 0) {
                delta += tipo === "confeccion" ? cantidad * precio : precio;
            }
        });
    });

    document.querySelectorAll(".articulo-item--readonly[data-tipo='confeccion']").forEach(artItem => {
        const cantInput = _artInput(artItem, "cantidad");
        if (!cantInput) return;
        const oldCant = parseFloat(cantInput.dataset.original || 1);
        const newCant = parseFloat(cantInput.value || 1);
        const diff    = newCant - oldCant;
        if (Math.abs(diff) < 0.001) return;

        artItem.querySelectorAll(".servicio-ro-item").forEach(srv => {
            if (srv.querySelector(".existing-delete-flag")?.value === "1") return;
            const precio = parseFloat(
                srv.querySelector(".servicio-ro-precio-input")?.value
                || srv.dataset.precioOriginal || 0
            );
            delta += precio * diff;
        });

        artItem.querySelectorAll(".agregar-servicios-existente .existing-servicio-item").forEach(fila => {
            const sel    = fila.querySelector("select");
            const precio = parseFloat(fila.querySelector(".precio-aplicado")?.value || 0);
            if (sel?.value && precio > 0) delta += diff * precio;
        });
    });

    document.querySelectorAll(".articulo-item--readonly[data-tipo='maquila']").forEach(artItem => {
        const cantInput = _artInput(artItem, "cantidad");
        const puInput   = _artInput(artItem, "precio_unitario");
        if (!cantInput || !puInput) return;
        const oldTotal = parseFloat(cantInput.dataset.original || 0) * parseFloat(puInput.dataset.original || 0);
        const newTotal = parseFloat(cantInput.value || 0) * parseFloat(puInput.value || 0);
        delta += newTotal - oldTotal;
    });

    return delta;
}


function hayCambios() {
    const form = document.getElementById("formEditarVenta");
    if (!form) return false;

    const fechaOriginal  = form.dataset.fechaOriginal || "";
    const [origDate, origHora] = fechaOriginal.split(" ");
    const fechaVis = document.getElementById("fecha_estimada_fecha_vis")?.value || "";
    const horaVis  = document.getElementById("fecha_estimada_hora_vis")?.value  || "";
    if (fechaVis !== (origDate || "") || horaVis !== (origHora || "")) return true;

    if (document.querySelectorAll("#articulos-container .articulo-item").length > 0) return true;

    if ([...document.querySelectorAll(".existing-servicio-item select")].some(s => s.value)) return true;

    if ([...document.querySelectorAll("[name^='art_edit']")]
        .some(inp => (inp.value || "").trim() !== (inp.dataset.original || "").trim())) return true;

    return [...document.querySelectorAll(".servicio-ro-item")].some(item => {
        if (item.querySelector(".existing-delete-flag")?.value === "1") return true;
        const orig  = parseFloat(item.dataset.precioOriginal || 0);
        const nuevo = parseFloat(item.querySelector(".servicio-ro-precio-input")?.value ?? orig);
        return Math.abs(nuevo - orig) > 0.001;
    });
}


function actualizarDeltaDisplay(totalActual) {
    const deltaExistentes = calcularDeltaExistentes();
    const deltaNuevos     = calcularDeltaNuevos();
    const nuevoTotal      = totalActual + deltaExistentes + deltaNuevos;

    const el = document.getElementById("total-venta");
    if (el) {
        el.textContent = `Total: $${nuevoTotal.toLocaleString("es-MX", {
            minimumFractionDigits: 2, maximumFractionDigits: 2
        })}`;
    }

    const btnGuardar = document.getElementById("btn-guardar");
    if (btnGuardar) btnGuardar.disabled = !hayCambios();
}


function agregarServicioExistente(idArt) {
    const contenedor = document.getElementById(`existingServiciosLista_${idArt}`);
    if (!contenedor) return;

    const j         = contenedor.querySelectorAll(".existing-servicio-item").length;
    const servicios = ventaState.serviciosGlobales;
    const optsHtml  = servicios.map(s => {
        const precio = s.precio_base ?? s.precio ?? 0;
        return `<option value="${s.id_servicio}" data-precio="${precio}">${escapeHtml(s.nombre)} ($${precio})</option>`;
    }).join("");

    contenedor.insertAdjacentHTML("beforeend", `
        <div class="existing-servicio-item servicio-item" data-index-servicio="${j}">
            <select name="existing_servicios[${idArt}][${j}][id_servicio]">
                <option value="">-- Selecciona servicio --</option>
                ${optsHtml}
            </select>
            <input type="number" min="0" step="0.01"
                   class="precio-aplicado"
                   name="existing_servicios[${idArt}][${j}][precio_aplicado]"
                   placeholder="Precio"
                   disabled data-editado="0">
            <button type="button" data-action="delete-existing-service" class="btn btn--danger btn--sm">
                <i data-lucide="x" width="14" height="14"></i>
            </button>
        </div>
    `);
    if (window.lucide) lucide.createIcons();
}


function _fmtFecha(fechaStr) {
    if (!fechaStr) return "—";
    const [fecha, hora] = fechaStr.split(" ");
    if (!fecha) return "—";
    const [y, m, d] = fecha.split("-");
    const mes = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"][parseInt(m,10)-1] || m;
    return hora ? `${parseInt(d,10)} ${mes} ${y} ${hora}` : `${parseInt(d,10)} ${mes} ${y}`;
}

function _cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }


function _buildSummary(card) {
    const tipo     = card.dataset.tipo;
    const get      = campo => _artInput(card, campo)?.value?.trim() || "";
    const srvCount = card.querySelectorAll(".servicio-ro-item:not(.servicio-ro-item--eliminado)").length;
    const srvStr   = srvCount ? `${srvCount} servicio${srvCount !== 1 ? "s" : ""}` : "";

    if (tipo === "calzado") {
        const nm  = [get("tipo"), get("marca")].filter(Boolean).join(" ");
        return [nm, get("material"), srvStr].filter(Boolean).join(" · ");
    }
    if (tipo === "confeccion") {
        const nm   = [get("tipo"), get("marca")].filter(Boolean).join(" ");
        const cant = get("cantidad");
        return [nm, cant ? `${cant} pzas` : "", srvStr].filter(Boolean).join(" · ");
    }
    if (tipo === "maquila") {
        const nm  = get("tipo");
        const cant = get("cantidad");
        const pu  = get("precio_unitario");
        const precio = pu ? `$${parseFloat(pu).toFixed(2)}` : "";
        return [nm, cant && precio ? `${cant} × ${precio}` : cant || precio].filter(Boolean).join(" · ");
    }
    return "";
}

function _abrirArticuloRo(card) {
    document.querySelectorAll(".articulo-item--readonly:not(.art-ro-collapsed)").forEach(other => {
        if (other !== card) _cerrarArticuloRo(other);
    });
    if (!card.classList.contains("art-ro-collapsed")) return;

    card.classList.remove("art-ro-collapsed");
    const body = card.querySelector(".art-ro-body");
    if (body) {
        body.classList.remove("is-closing");
        body.classList.add("is-opening");
        body.addEventListener("animationend", () => body.classList.remove("is-opening"), { once: true });
    }
}

function _cerrarArticuloRo(card) {
    if (card.classList.contains("art-ro-collapsed")) return;
    const body = card.querySelector(".art-ro-body");
    if (body) {
        body.classList.remove("is-opening");
        body.classList.add("is-closing");
        body.addEventListener("animationend", () => {
            body.classList.remove("is-closing");
            card.classList.add("art-ro-collapsed");
            const summary = card.querySelector(".art-ro-summary");
            if (summary) summary.textContent = _buildSummary(card);
        }, { once: true });
    } else {
        card.classList.add("art-ro-collapsed");
    }
}


function construirResumen(form, totalActual, totalPagado) {
    const fechaOriginal = form.dataset.fechaOriginal || "";
    const fechaVis      = document.getElementById("fecha_estimada_fecha_vis").value;
    const horaVis       = document.getElementById("fecha_estimada_hora_vis").value;
    const fechaNueva    = (fechaVis && horaVis) ? `${fechaVis} ${horaVis}` : "";
    const fechaCambiada = !!(fechaNueva && fechaNueva !== fechaOriginal);

    const deltaExistentes = calcularDeltaExistentes();
    const deltaNuevos     = calcularDeltaNuevos();
    const nuevoTotal      = totalActual + deltaExistentes + deltaNuevos;
    const deltaTotal      = deltaExistentes + deltaNuevos;

    const numNuevosArts = document.querySelectorAll("#articulos-container .articulo-item").length;

    let numNuevosSrv = 0;
    const detalleNuevosSrv = [];
    document.querySelectorAll(".agregar-servicios-existente").forEach(box => {
        const num    = box.dataset.articuloNum;
        const tipo   = box.dataset.tipo;
        const nombres = [...box.querySelectorAll(".existing-servicio-item select")]
            .filter(s => s.value)
            .map(s => escapeHtml((s.selectedOptions[0]?.text || "?").replace(/\s*\(\$[\d.,]+\)$/, "")));
        if (nombres.length > 0) { numNuevosSrv += nombres.length; detalleNuevosSrv.push({ num, tipo, nombres }); }
    });

    const allEditItems = [];
    const allDelItems  = [];
    document.querySelectorAll(".articulo-item--readonly").forEach((artItem, artIdx) => {
        artItem.querySelectorAll(".servicio-ro-item").forEach(item => {
            const nombre = escapeHtml(item.dataset.nombre || "?");
            const orig   = parseFloat(item.dataset.precioOriginal || 0);
            if (item.querySelector(".existing-delete-flag")?.value === "1") {
                allDelItems.push(`Art. #${artIdx + 1} — ${nombre} ($${orig.toFixed(2)})`);
            } else {
                const nuevo = parseFloat(item.querySelector(".servicio-ro-precio-input")?.value ?? orig);
                if (Math.abs(nuevo - orig) > 0.001) {
                    allEditItems.push(`${nombre}: $${orig.toFixed(2)} → $${nuevo.toFixed(2)}`);
                }
            }
        });
    });

    const artsConDetallesEditados = [];
    document.querySelectorAll(".articulo-item--readonly").forEach((card, idx) => {
        const changed = [...card.querySelectorAll("[name^='art_edit']")]
            .some(inp => (inp.value || "").trim() !== (inp.dataset.original || "").trim());
        if (changed) artsConDetallesEditados.push(idx + 1);
    });

    const sinCambios = !fechaCambiada && numNuevosArts === 0 && numNuevosSrv === 0
                     && allEditItems.length === 0 && allDelItems.length === 0
                     && artsConDetallesEditados.length === 0;
    if (sinCambios) return null;

    const fmt = v => v.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const tr  = (cls, icon, label, value) =>
        `<tr class="${cls}">
            <td class="resumen-tabla__clave"><i data-lucide="${icon}" width="13" height="13"></i> ${label}</td>
            <td class="resumen-tabla__valor">${value}</td>
        </tr>`;

    let filas = "";

    if (fechaCambiada) {
        filas += tr("resumen-tr--fecha", "calendar", "Fecha",
            `${_fmtFecha(fechaOriginal)} → ${_fmtFecha(fechaNueva)}`);
    }

    if (numNuevosArts > 0) {
        filas += tr("resumen-tr--art", "package", "Artículos nuevos",
            `${numNuevosArts} artículo${numNuevosArts > 1 ? "s" : ""} agregado${numNuevosArts > 1 ? "s" : ""}`);
    }

    if (detalleNuevosSrv.length > 0) {
        const val = detalleNuevosSrv.map(({ num, tipo, nombres }) =>
            `Art. #${num} (${_cap(tipo)}): ${nombres.join(", ")}`
        ).join(" · ");
        filas += tr("resumen-tr--srv", "wrench", "Servicios nuevos", val);
    }

    if (allEditItems.length > 0) {
        filas += tr("resumen-tr--precio", "pencil",
            `Precio${allEditItems.length > 1 ? "s" : ""} editado${allEditItems.length > 1 ? "s" : ""}`,
            allEditItems.join(" · "));
    }

    if (allDelItems.length > 0) {
        filas += tr("resumen-tr--del", "trash-2",
            `Servicio${allDelItems.length > 1 ? "s" : ""} eliminado${allDelItems.length > 1 ? "s" : ""}`,
            allDelItems.join(" · "));
    }

    if (artsConDetallesEditados.length > 0) {
        filas += tr("resumen-tr--art", "file-edit", "Detalles editados",
            `Art. #${artsConDetallesEditados.join(", #")}`);
    }

    if (Math.abs(deltaTotal) > 0.001) {
        const positivo = deltaTotal > 0;
        const signo    = positivo ? "+" : "−";
        const cls      = positivo ? "resumen-delta" : "resumen-delta resumen-delta--neg";
        filas += tr("resumen-tr--total", "receipt", "Total",
            `$${fmt(totalActual)} → $${fmt(nuevoTotal)}<span class="${cls}"> ${signo}$${fmt(Math.abs(deltaTotal))}</span>`);
    }

    return `<table class="resumen-tabla"><tbody>${filas}</tbody></table>`;
}


const _ETIQUETAS_CAMPO = {
    tipo: "Tipo", marca: "Marca", material: "Material",
    color_base: "Color base", cantidad: "Cantidad", precio_unitario: "Precio unitario",
};

const _CAMPOS_REQUERIDOS = {
    calzado:    ["tipo", "marca", "material", "color_base"],
    confeccion: ["tipo", "marca", "material", "color_base", "cantidad"],
    maquila:    ["tipo", "cantidad", "precio_unitario"],
};

// Valor mínimo permitido para campos numéricos (exclusive: debe ser >= min)
const _CAMPOS_MINIMO = { cantidad: 1, precio_unitario: 0.01 };

function _campoEsInvalido(campo, inp) {
    const raw = (inp.value || "").trim();
    if (raw === "") return true;
    if (campo in _CAMPOS_MINIMO) {
        const val = parseFloat(raw);
        if (isNaN(val) || val < _CAMPOS_MINIMO[campo]) return true;
    }
    return false;
}

function _validarCamposObligatorios() {
    const tarjetas = document.querySelectorAll(".articulo-item--readonly");
    for (let i = 0; i < tarjetas.length; i++) {
        const card      = tarjetas[i];
        const tipo      = card.dataset.tipo;
        const requeridos = _CAMPOS_REQUERIDOS[tipo];
        if (!requeridos) continue;
        for (const campo of requeridos) {
            const inp = _artInput(card, campo);
            if (!inp) continue;
            if (_campoEsInvalido(campo, inp)) {
                const etiq = _ETIQUETAS_CAMPO[campo] || campo;
                const sufijo = campo in _CAMPOS_MINIMO ? " debe ser mayor a 0." : " es obligatorio.";
                return `Art. #${i + 1}: "${etiq}"${sufijo}`;
            }
        }
    }
    return null;
}

/** Marca con field--invalid los campos obligatorios inválidos dentro de una tarjeta. */
function _marcarCamposObligatorios(card) {
    const tipo      = card.dataset.tipo;
    const requeridos = _CAMPOS_REQUERIDOS[tipo] || [];
    card.querySelectorAll("[name^='art_edit']").forEach(inp => {
        const m = inp.name.match(/\[(\w+)\]$/);
        if (!m) return;
        const campo = m[1];
        if (requeridos.includes(campo)) {
            const invalido = _campoEsInvalido(campo, inp);
            inp.classList.toggle("field--invalid", invalido);
            if (invalido) inp.classList.remove("field--editado");
        }
    });
}

/**
 * Valida servicios en artículos existentes (calzado/confeccion):
 *   - Al menos 1 servicio activo por artículo
 *   - Ningún servicio con precio ≤ 0
 * Devuelve string de error o null si todo está bien.
 */
function _validarServiciosExistentes() {
    const tarjetas = document.querySelectorAll(".articulo-item--readonly");
    for (let i = 0; i < tarjetas.length; i++) {
        const card = tarjetas[i];
        const tipo = card.dataset.tipo;
        if (tipo !== "calzado" && tipo !== "confeccion") continue;

        const num = i + 1;

        // Servicios existentes no marcados para eliminar
        const srvActivos = [...card.querySelectorAll(".servicio-ro-item")]
            .filter(item => !item.classList.contains("servicio-ro-item--eliminado"));

        // Servicios nuevos agregados en esta sesión (con select elegido)
        const srvNuevos = [...card.querySelectorAll(".existing-servicio-item select")]
            .filter(sel => sel.value);

        const totalServicios = srvActivos.length + srvNuevos.length;

        if (totalServicios === 0) {
            return `El artículo #${num} (${tipo}) debe tener al menos 1 servicio activo.`;
        }

        // Precios de servicios existentes activos
        for (const item of srvActivos) {
            const input = item.querySelector(".servicio-ro-precio-input");
            const precio = parseFloat(input?.value ?? 0);
            if (isNaN(precio) || precio <= 0) {
                const nombre = item.dataset.nombre || `Servicio`;
                return `Art. #${num}: el precio de "${nombre}" debe ser mayor a $0.`;
            }
        }

        // Precios de servicios nuevos
        for (const fila of card.querySelectorAll(".existing-servicio-item")) {
            const sel    = fila.querySelector("select");
            if (!sel?.value) continue;
            const precio = parseFloat(fila.querySelector(".precio-aplicado")?.value ?? 0);
            if (isNaN(precio) || precio <= 0) {
                const nombre = sel.selectedOptions[0]?.text || "Servicio nuevo";
                return `Art. #${num}: el precio de "${nombre}" debe ser mayor a $0.`;
            }
        }
    }
    return null;
}

function _motivosBloqueoGuardar(totalActual, totalPagado) {
    const motivos = [];
    if (!hayCambios()) {
        motivos.push("Sin cambios que guardar");
        return motivos;
    }
    const fmt = v => "$" + v.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const nuevoTotal = totalActual + calcularDeltaExistentes() + calcularDeltaNuevos();
    if (nuevoTotal < totalPagado) {
        motivos.push(`Total ${fmt(nuevoTotal)} menor al pagado ${fmt(totalPagado)}`);
    }
    const errCampos = _validarCamposObligatorios();
    if (errCampos) motivos.push(errCampos);
    const errSrv = _validarServiciosExistentes();
    if (errSrv) motivos.push(errSrv);
    return motivos;
}

document.addEventListener("DOMContentLoaded", async () => {
    const form        = document.getElementById("formEditarVenta");
    const idVenta     = form.dataset.ventaId;
    const totalActual = parseFloat(form.dataset.totalActual || 0);
    const totalPagado = parseFloat(form.dataset.totalPagado || 0);

    ventaState.negocioSeleccionado = document.getElementById("id_negocio").value;
    await cargarServicios();

    // ── Botón guardar con tooltip (igual que btn-crear en ventas_crear) ──
    const btnGuardarEl = document.getElementById("btn-guardar");
    const msgBloqueo   = document.createElement("span");
    msgBloqueo.id      = "mensaje-bloqueo-guardar";
    msgBloqueo.style.display = "none";
    document.body.appendChild(msgBloqueo);

    const btnTooltip = document.createElement("div");
    btnTooltip.className = "btn-tooltip";
    document.body.appendChild(btnTooltip);

    btnGuardarEl.addEventListener("mouseover", () => {
        if (!btnGuardarEl.disabled) return;
        const text = msgBloqueo.textContent?.trim();
        if (!text) return;
        btnTooltip.textContent = text;
        btnTooltip.classList.add("visible");
        requestAnimationFrame(() => {
            const rect = btnGuardarEl.getBoundingClientRect();
            btnTooltip.style.left = Math.max(8, rect.left + rect.width / 2 - btnTooltip.offsetWidth / 2) + "px";
            btnTooltip.style.top  = (rect.top - btnTooltip.offsetHeight - 12) + "px";
        });
    });
    btnGuardarEl.addEventListener("mouseleave", () => btnTooltip.classList.remove("visible"));

    const actualizarUI = () => {
        actualizarDeltaDisplay(totalActual);
        const motivos = _motivosBloqueoGuardar(totalActual, totalPagado);
        btnGuardarEl.disabled      = motivos.length > 0;
        msgBloqueo.textContent     = motivos[0] || "";
    };

    actualizarUI();

    const sincFecha = () => {
        document.getElementById("fecha_estimada_fecha_hidden").value =
            document.getElementById("fecha_estimada_fecha_vis").value;
        document.getElementById("fecha_estimada_hora_hidden").value =
            document.getElementById("fecha_estimada_hora_vis").value;
        actualizarUI();
    };
    document.getElementById("fecha_estimada_fecha_vis").addEventListener("change", sincFecha);
    document.getElementById("fecha_estimada_hora_vis").addEventListener("change", sincFecha);

    document.getElementById("btn-agregar-articulo").addEventListener("click", () => {
        agregarArticulo();
        actualizarUI();
    });

    const articulosContainer = document.getElementById("articulos-container");

    articulosContainer.addEventListener("change", e => {
        const sel = e.target;
        if (sel.tagName !== "SELECT" || !sel.closest(".servicio-item")) return;
        const box           = sel.closest(".servicios-box");
        const indexArticulo = parseInt(box?.dataset?.articulo ?? "0");
        onChangeServicio(sel, indexArticulo);
        actualizarUI();
        const art = sel.closest(".articulo-item");
        if (art) validarArticuloVisual(art);
    });

    articulosContainer.addEventListener("input", e => {
        if (e.target.classList.contains("precio-aplicado")) marcarPrecioEditado(e.target);
        actualizarUI();
        const art = e.target.closest(".articulo-item");
        if (art) validarArticuloVisual(art);
    });

    articulosContainer.addEventListener("click", e => {
        const btn = e.target.closest("[data-action]");
        if (!btn) return;
        const action = btn.dataset.action;
        if (action === "delete-article") {
            eliminarArticulo(btn);
        } else if (action === "add-service") {
            const box = btn.closest(".servicios-box");
            agregarServicio(parseInt(box?.dataset?.articulo ?? "0"));
        } else if (action === "delete-service") {
            const box = btn.closest(".servicios-box");
            eliminarServicioPro(btn, parseInt(box?.dataset?.articulo ?? "0"));
        }
        actualizarUI();
    });

    document.addEventListener("click", e => {
        const addBtn = e.target.closest(".js-add-existing-service");
        if (addBtn) {
            agregarServicioExistente(addBtn.dataset.articuloId);
            actualizarUI();
            return;
        }

        const delNewBtn = e.target.closest("[data-action='delete-existing-service']");
        if (delNewBtn) {
            delNewBtn.closest(".existing-servicio-item").remove();
            actualizarUI();
            return;
        }

        const delSrvBtn = e.target.closest(".btn-delete-existing-srv");
        if (delSrvBtn) {
            const item = delSrvBtn.closest(".servicio-ro-item");
            if (!item) return;
            const flag    = item.querySelector(".existing-delete-flag");
            const input   = item.querySelector(".servicio-ro-precio-input");
            const deleting = flag?.value !== "1";

            if (flag)  flag.value    = deleting ? "1" : "0";
            if (input) input.disabled = deleting;
            item.classList.toggle("servicio-ro-item--eliminado", deleting);

            delSrvBtn.innerHTML = deleting
                ? '<i data-lucide="undo-2" width="14" height="14"></i>'
                : '<i data-lucide="x" width="14" height="14"></i>';
            delSrvBtn.classList.toggle("btn--danger", !deleting);
            delSrvBtn.classList.toggle("btn--secondary", deleting);
            if (window.lucide) lucide.createIcons();
            actualizarUI();
        }
    });

    document.addEventListener("change", e => {
        const fila = e.target.closest(".existing-servicio-item");
        if (!fila || e.target.tagName !== "SELECT") return;
        const inputPrecio = fila.querySelector(".precio-aplicado");
        const opt         = e.target.selectedOptions[0];
        if (!opt?.value) {
            if (inputPrecio) { inputPrecio.value = ""; inputPrecio.disabled = true; }
        } else if (inputPrecio) {
            inputPrecio.disabled = false;
            if (inputPrecio.dataset.editado !== "1") {
                inputPrecio.value = parseFloat(opt.dataset.precio || 0);
            }
        }
        actualizarUI();
    });

    document.addEventListener("input", e => {
        if (e.target.closest(".existing-servicio-item") && e.target.classList.contains("precio-aplicado")) {
            e.target.dataset.editado = "1";
        }
        if (e.target.closest(".servicio-ro-item") || e.target.closest(".existing-servicio-item")) {
            actualizarUI();
        }
        if (e.target.matches("[name^='art_edit']")) {
            actualizarUI();
            const orig = (e.target.dataset.original || "").trim();
            const curr = (e.target.value || "").trim();
            e.target.classList.toggle("field--editado", orig !== curr && curr !== "");
            const card = e.target.closest(".articulo-item--readonly");
            if (card) _marcarCamposObligatorios(card);
        }
    });

    document.addEventListener("click", e => {
        if (e.target.closest("#btn-agregar-articulo")) return;
        const abierto = document.querySelector(".articulo-item.abierto");
        if (!abierto) return;
        if (e.composedPath().includes(abierto)) return;
        import('./ventas_articulos.js').then(m => m.cerrarArticulo(abierto));
    });

    form.addEventListener("submit", e => {
        e.preventDefault();
        if (ventaState.enProceso) return;

        const resumenHtml = construirResumen(form, totalActual, totalPagado);
        if (!resumenHtml) return;

        const resumenEl = document.getElementById("resumen-cambios");
        if (resumenEl) {
            resumenEl.innerHTML = resumenHtml;
            if (window.lucide) lucide.createIcons();
        }

        const btnOld = document.getElementById("btnConfirmarEdicion");
        const btnNew = btnOld.cloneNode(true);
        btnOld.parentNode.replaceChild(btnNew, btnOld);

        btnNew.addEventListener("click", async () => {
            cerrarModal("modalConfirmarEdicion");
            ventaState.enProceso = true;
            const btnGuardar = document.getElementById("btn-guardar");
            const textoOrig  = btnGuardar?.innerHTML;
            if (btnGuardar) { btnGuardar.disabled = true; btnGuardar.textContent = "Guardando..."; }

            try {
                const res  = await fetch(`/ventas/pendientes/${idVenta}/editar`, {
                    method: "POST",
                    body:   new FormData(form),
                });
                const data = await res.json();
                if (!data.ok) {
                    mostrarFeedback("Error: " + (data.error || "No se pudo guardar"), "error");
                    ventaState.enProceso = false;
                    if (btnGuardar) btnGuardar.innerHTML = textoOrig;
                    actualizarUI();
                    return;
                }
                redirigirConFeedback("/ventas/pendientes", "Venta actualizada correctamente.", "success", 300);
            } catch {
                mostrarFeedback("Error inesperado al guardar.", "error");
                ventaState.enProceso = false;
                if (btnGuardar) btnGuardar.innerHTML = textoOrig;
                actualizarUI();
            }
        });

        abrirModal("modalConfirmarEdicion");
    });

    document.addEventListener("click", e => {
        const card = e.target.closest(".articulo-item--readonly");

        if (!card) {
            document.querySelectorAll(".articulo-item--readonly:not(.art-ro-collapsed)")
                .forEach(c => _cerrarArticuloRo(c));
            return;
        }

        if (card.classList.contains("art-ro-collapsed")) {
            _abrirArticuloRo(card);
        } else if (e.target.closest(".art-ro-header")) {
            _cerrarArticuloRo(card);
        }
    });

    initNavigationGuard(() => !ventaState.enProceso && hayCambios());
});
