import { abrirModal, cerrarModal } from '../components/modal.js';

const _TOAST_KEY = "_pendingToast";

export function escapeHtml(str) {
    const d = document.createElement("div");
    d.appendChild(document.createTextNode(String(str ?? "")));
    return d.innerHTML;
}

export function normalizar(txt) {
    return (txt || "").toLowerCase()
        .normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
}

export function csrfFetch(url, options = {}) {
    const tokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (!tokenMeta) {
        console.error("CSRF token not found");
        return fetch(url, options);
    }

    const token = tokenMeta.getAttribute("content");

    options.headers = {
        ...options.headers,
        "X-CSRFToken": token,
        "Content-Type": "application/json"
    };

    return fetch(url, options);
}


function _getToastContainer() {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        document.body.appendChild(container);
    }
    return container;
}

function _scheduleAlertDismiss(el) {
    if (el.dataset.dismissScheduled) return;
    el.dataset.dismissScheduled = "1";

    el.addEventListener("click", () => el.remove(), { once: true });
    setTimeout(() => {
        el.style.transition = "opacity 0.5s ease, transform 0.5s ease";
        el.style.opacity    = "0";
        el.style.transform  = "translateY(-10px)";
    }, 4500);
    setTimeout(() => el.remove(), 5000);
}

function _appendToast(texto, tipo) {
    const div = document.createElement("div");
    div.className = `alert ${tipo}`;
    div.textContent = texto;
    _getToastContainer().appendChild(div);
    _scheduleAlertDismiss(div);
}

export function mostrarFeedback(texto, tipo = "success") {
    _appendToast(texto, tipo);
}


export function recargarConFeedback(texto, tipo = "success", delay = 300) {
    try {
        sessionStorage.setItem(_TOAST_KEY, JSON.stringify({ texto, tipo }));
    } catch {}
    setTimeout(() => location.reload(), delay);
}


export function apiAction({
    url, method = "POST", body = null,
    msgOk = null, msgError = "Error al realizar la acción.",
    reload = false, reloadDelay = 1200,
    onSuccess = null, onError = null,
    loadingBtn = null,
    timeoutMs = 30_000
}) {
    if (loadingBtn) {
        loadingBtn.disabled = true;
        loadingBtn._textoOriginal = loadingBtn.innerHTML;
        loadingBtn.innerHTML = '<span class="spinner"></span>';
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    const opts = { method, signal: controller.signal };
    if (body) {
        opts.body = JSON.stringify(body);
    }

    const restoreBtn = () => {
        if (loadingBtn) {
            loadingBtn.disabled  = false;
            loadingBtn.innerHTML = loadingBtn._textoOriginal;
        }
    };

    csrfFetch(url, opts)
        .then(r => {
            clearTimeout(timer);
            const ct = r.headers.get("content-type") || "";
            if (!ct.includes("application/json")) {
                throw new Error("Respuesta inesperada del servidor.");
            }
            return r.json();
        })
        .then(res => {
            restoreBtn();
            if (res.ok) {
                if (onSuccess) onSuccess(res);
                if (reload) {
                    recargarConFeedback(msgOk || res.message || "", "success", reloadDelay);
                } else {
                    if (msgOk) mostrarFeedback(msgOk, "success");
                }
            } else {
                mostrarFeedback(res.error || msgError, "error");
                if (onError) onError(res);
            }
        })
        .catch(err => {
            clearTimeout(timer);
            restoreBtn();
            const msg = err.name === "AbortError"
                ? "La solicitud tardó demasiado. Intenta de nuevo."
                : (err.message || "Error de conexión.");
            mostrarFeedback(msg, "error");
        });
}


export function crearEliminarHandler(modalId) {
    let _pendingUrl = null;
    let _pendingRow = null;
    return {
        confirmar(url, rowEl = null) {
            _pendingUrl = url;
            _pendingRow = rowEl;
            abrirModal(modalId);
        },
        ejecutar() {
            if (!_pendingUrl) return;
            const url = _pendingUrl;
            const row = _pendingRow;
            _pendingUrl = null;
            _pendingRow = null;
            if (row) {
                row.classList.add("row--removing");
                setTimeout(() => { location.href = url; }, 300);
            } else {
                location.href = url;
            }
        }
    };
}


export function confirmarEliminarVenta(idVenta) {
    const btnConf = document.getElementById("btnConfirmarEliminar");
    if (!btnConf) return;

    abrirModal("modalEliminarVenta");

    const nuevo = btnConf.cloneNode(true);
    btnConf.parentNode.replaceChild(nuevo, btnConf);

    nuevo.addEventListener("click", () => {
        cerrarModal("modalEliminarVenta");
        apiAction({
            url:      `/ventas/eliminar/${idVenta}`,
            msgOk:    "Venta eliminada correctamente.",
            msgError: "No se pudo eliminar la venta.",
            reload:   true
        });
    });
}


export function initModalForm(form, submitBtn) {
    function validate() {
        const fields = Array.from(form.querySelectorAll("[required]"));
        let allValid = true;
        fields.forEach(field => {
            const empty = field.value.trim() === "";
            field.classList.toggle("field--invalid", empty);
            if (empty) allValid = false;
        });
        form.querySelectorAll(".field--invalid").forEach(el => {
            if (!el.required) el.classList.remove("field--invalid");
        });
        if (submitBtn) submitBtn.disabled = !allValid;
        return allValid;
    }

    form.addEventListener("input", validate);
    form.addEventListener("change", validate);
    validate();
    return validate;
}


export function shakeEl(el) {
    if (!el) return;
    el.classList.remove("shake");
    void el.offsetWidth;
    el.classList.add("shake");
    el.addEventListener("animationend", () => el.classList.remove("shake"), { once: true });
}


export function countUp(el, target, monetary = false, duration = 900) {
    const start = performance.now();
    const fmt = monetary
        ? v => "$" + v.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        : v => Math.floor(v).toLocaleString("es-MX");
    function tick(now) {
        const ease = 1 - Math.pow(1 - Math.min((now - start) / duration, 1), 3);
        el.textContent = fmt(target * ease);
        if (ease < 1) requestAnimationFrame(tick);
        else el.textContent = fmt(target);
    }
    requestAnimationFrame(tick);
}
