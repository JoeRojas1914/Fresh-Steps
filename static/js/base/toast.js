// Toasts: mensajes flotantes que se cierran solos (o con un clic).
// Fuente única: helpers.js importa appendToast y TOAST_KEY de aquí.

export const TOAST_KEY = "_pendingToast";

function _getContainer() {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        document.body.appendChild(container);
    }
    return container;
}

function _agregarBarra(el) {
    if (el.querySelector(".toast-progress")) return;
    const bar = document.createElement("div");
    bar.className = "toast-progress";
    el.appendChild(bar);
}

function _scheduleDismiss(el) {
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

export function appendToast(texto, tipo) {
    if (!texto) return;
    const div = document.createElement("div");
    div.className = `alert ${tipo}`;
    div.textContent = texto;
    _agregarBarra(div);
    _getContainer().appendChild(div);
    _scheduleDismiss(div);
}

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("toast-container")) return;
    const container = _getContainer();

    // Mensaje guardado antes de recargar o redirigir (recargarConFeedback)
    try {
        const raw = sessionStorage.getItem(TOAST_KEY);
        if (raw) {
            sessionStorage.removeItem(TOAST_KEY);
            const { texto, tipo } = JSON.parse(raw);
            appendToast(texto, tipo);
        }
    } catch {}

    // Mensajes flash que vienen en el HTML
    document.querySelectorAll(".alert").forEach(alert => {
        if (!container.contains(alert)) {
            _agregarBarra(alert);
            container.appendChild(alert);
        }
        _scheduleDismiss(alert);
    });
});
