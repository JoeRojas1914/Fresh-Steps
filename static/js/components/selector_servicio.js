import { escapeHtml } from '../base/helpers.js';

const MIN_PARA_FILTRO = 8;

let _abierto = null; 

function _fmtPrecio(p) {
    return "$" + (parseFloat(p) || 0).toLocaleString("es-MX", {
        minimumFractionDigits: 2, maximumFractionDigits: 2,
    });
}

function _sincronizar(select) {
    const boton = select._srvBoton;
    if (!boton) return;
    const opt = select.selectedOptions[0];
    const nombre = boton.querySelector(".srv-picker__nombre");
    const precio = boton.querySelector(".srv-picker__precio");
    if (opt?.value) {
        nombre.textContent = opt.dataset.nombre || opt.text;
        precio.textContent = _fmtPrecio(opt.dataset.precio);
        boton.classList.remove("is-vacio");
    } else {
        nombre.textContent = opt?.text || "-- Selecciona servicio --";
        precio.textContent = "";
        boton.classList.add("is-vacio");
    }
    boton.disabled = select.disabled;
}

function _cerrar({ enfocar = false } = {}) {
    if (!_abierto) return;
    const { boton, contenedor } = _abierto;
    contenedor.remove();
    boton.setAttribute("aria-expanded", "false");
    boton.classList.remove("is-abierto");
    if (enfocar) boton.focus();
    _abierto = null;
}

function _posicionar() {
    if (!_abierto) return;
    const { boton, contenedor } = _abierto;
    const r      = boton.getBoundingClientRect();
    const alto   = contenedor.offsetHeight;
    const abajo  = window.innerHeight - r.bottom;
    const arriba = abajo < alto + 8 && r.top > abajo;
    contenedor.style.left  = `${Math.max(8, r.left)}px`;
    contenedor.style.width = `${Math.max(r.width, 280)}px`;
    contenedor.style.top   = arriba ? `${r.top - alto - 4}px` : `${r.bottom + 4}px`;
}

function _items() {
    return _abierto
        ? [..._abierto.lista.querySelectorAll(".srv-picker__item:not([hidden]):not(.is-deshabilitado)")]
        : [];
}

function _marcar(item) {
    _abierto.lista.querySelectorAll(".is-activo").forEach(el => el.classList.remove("is-activo"));
    if (!item) return;
    item.classList.add("is-activo");
    item.scrollIntoView({ block: "nearest" });
}

function _elegir(valor) {
    const { select } = _abierto;
    _cerrar({ enfocar: true });
    if (select.value === valor) return;
    select.value = valor;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    _sincronizar(select);
}

function _abrir(select) {
    _cerrar();
    const boton   = select._srvBoton;
    const opciones = [...select.options].filter(o => o.value);

    const contenedor = document.createElement("div");
    contenedor.className = "srv-picker__panel";

    const filtroHtml = opciones.length >= MIN_PARA_FILTRO
        ? `<input type="text" class="srv-picker__filtro" placeholder="Buscar servicio..." autocomplete="off" aria-label="Buscar servicio">`
        : "";

    const itemsHtml = opciones.map(o => `
        <li class="srv-picker__item${o.disabled ? " is-deshabilitado" : ""}${o.value === select.value ? " is-seleccionado" : ""}"
            role="option" data-value="${escapeHtml(o.value)}"
            aria-selected="${o.value === select.value}" aria-disabled="${o.disabled}"
            ${o.disabled ? 'title="Ya está agregado en este artículo"' : ""}>
            <span class="srv-picker__item-nombre">${escapeHtml(o.dataset.nombre || o.text)}</span>
            <span class="srv-picker__item-precio">${_fmtPrecio(o.dataset.precio)}</span>
        </li>`).join("");

    contenedor.innerHTML = `
        ${filtroHtml}
        <ul class="srv-picker__lista" role="listbox">
            ${itemsHtml || '<li class="srv-picker__vacio">No hay servicios para este negocio</li>'}
        </ul>
        <div class="srv-picker__vacio" hidden>Sin resultados</div>`;
    document.body.appendChild(contenedor);

    contenedor.addEventListener("click", e => {
        e.stopPropagation();
        const item = e.target.closest(".srv-picker__item");
        if (item && !item.classList.contains("is-deshabilitado")) _elegir(item.dataset.value);
    });

    _abierto = {
        select, boton, contenedor,
        lista:  contenedor.querySelector(".srv-picker__lista"),
        filtro: contenedor.querySelector(".srv-picker__filtro"),
    };
    boton.setAttribute("aria-expanded", "true");
    boton.classList.add("is-abierto");
    _posicionar();

    _marcar(contenedor.querySelector(".is-seleccionado:not(.is-deshabilitado)") || _items()[0]);
    (_abierto.filtro || boton).focus();
}

function _filtrar(texto) {
    const q = texto.trim().toLocaleLowerCase("es")
        .normalize("NFD").replace(/[̀-ͯ]/g, "");
    let visibles = 0;
    _abierto.lista.querySelectorAll(".srv-picker__item").forEach(li => {
        const nombre = li.querySelector(".srv-picker__item-nombre").textContent
            .toLocaleLowerCase("es").normalize("NFD").replace(/[̀-ͯ]/g, "");
        li.hidden = !!q && !nombre.includes(q);
        if (!li.hidden) visibles++;
    });
    _abierto.contenedor.querySelector(":scope > .srv-picker__vacio").hidden = visibles > 0;
    _marcar(_items()[0]);
}

function _teclado(e) {
    if (!_abierto) return;
    const items  = _items();
    const actual = _abierto.lista.querySelector(".is-activo");
    const idx    = items.indexOf(actual);

    if (e.key === "ArrowDown") {
        e.preventDefault();
        _marcar(items[Math.min(idx + 1, items.length - 1)] || items[0]);
    } else if (e.key === "ArrowUp") {
        e.preventDefault();
        _marcar(items[Math.max(idx - 1, 0)]);
    } else if (e.key === "Enter") {
        e.preventDefault();
        if (actual) _elegir(actual.dataset.value);
    } else if (e.key === "Escape") {
        e.preventDefault();
        _cerrar({ enfocar: true });
    } else if (e.key === "Tab") {
        _cerrar();
    }
}

export function mejorarSelectServicio(select) {
    if (select._srvBoton) return;

    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "srv-picker__btn is-vacio";
    boton.setAttribute("aria-haspopup", "listbox");
    boton.setAttribute("aria-expanded", "false");
    boton.innerHTML = `
        <span class="srv-picker__nombre"></span>
        <span class="srv-picker__precio"></span>
        <i data-lucide="chevron-down" width="16" height="16" class="srv-picker__chevron"></i>`;

    select.classList.add("srv-picker__nativo");
    select.tabIndex = -1;
    select.after(boton);
    select._srvBoton = boton;
    _sincronizar(select);
    if (window.lucide) lucide.createIcons();

    boton.addEventListener("click", () => {
        if (_abierto?.select === select) _cerrar();
        else _abrir(select);
    });
    boton.addEventListener("keydown", e => {
        if (!_abierto && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
            e.preventDefault();
            e.stopPropagation();  
            _abrir(select);
        }
    });
}


function _mejorarEn(raiz) {
    if (raiz.matches?.("select.select-servicio")) mejorarSelectServicio(raiz);
    raiz.querySelectorAll?.("select.select-servicio").forEach(mejorarSelectServicio);
}

_mejorarEn(document);
new MutationObserver(mutaciones => {
    for (const m of mutaciones) m.addedNodes.forEach(n => n.nodeType === 1 && _mejorarEn(n));
}).observe(document.body, { childList: true, subtree: true });

document.addEventListener("change", e => {
    if (e.target.matches?.("select.select-servicio")) _sincronizar(e.target);
});

document.addEventListener("click", e => {
    if (_abierto && !_abierto.boton.contains(e.target)) _cerrar();
});

document.addEventListener("input", e => {
    if (_abierto && e.target === _abierto.filtro) _filtrar(e.target.value);
});

document.addEventListener("keydown", _teclado);
window.addEventListener("resize", () => _cerrar());
document.addEventListener("scroll", e => {
    if (_abierto && !_abierto.contenedor.contains(e.target)) _cerrar();
}, true);
