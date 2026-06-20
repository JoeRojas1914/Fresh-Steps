const _TOAST_KEY = "_pendingToast";

function _getContainer() {
    return document.getElementById("toast-container");
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

function _appendToast(texto, tipo) {
    const container = _getContainer();
    if (!container || !texto) return;
    const div = document.createElement("div");
    div.className = `alert ${tipo}`;
    div.textContent = texto;
    const bar = document.createElement("div");
    bar.className = "toast-progress";
    div.appendChild(bar);
    container.appendChild(div);
    _scheduleDismiss(div);
}

document.addEventListener("DOMContentLoaded", () => {
    const container = _getContainer();
    if (!container) return;

    try {
        const raw = sessionStorage.getItem(_TOAST_KEY);
        if (raw) {
            sessionStorage.removeItem(_TOAST_KEY);
            const { texto, tipo } = JSON.parse(raw);
            _appendToast(texto, tipo);
        }
    } catch {}

    document.querySelectorAll(".alert").forEach(alert => {
        if (!container.contains(alert)) {
            container.appendChild(alert);
        }
        _scheduleDismiss(alert);
    });
});
