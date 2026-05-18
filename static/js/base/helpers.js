window.escapeHtml = function (str) {
    const d = document.createElement("div");
    d.appendChild(document.createTextNode(String(str ?? "")));
    return d.innerHTML;
};

window.normalizar = function (txt) {
    return (txt || "").toLowerCase()
        .normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
};

window.csrfFetch = function (url, options = {}) {

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
};


window.mostrarFeedback = function (texto, tipo = "success") {
    const anchor =
        document.querySelector(".page-content > .filtro-box") ||
        document.querySelector(".page-content > h1") ||
        document.querySelector(".page-content");

    const div = document.createElement("div");
    div.className = `alert ${tipo}`;
    div.textContent = texto;
    div.style.animation = "slideIn 0.25s ease";

    if (anchor && anchor.parentNode) {
        anchor.parentNode.insertBefore(div, anchor);
    } else {
        document.body.prepend(div);
    }

    setTimeout(() => {
        div.style.transition = "opacity 0.5s ease, transform 0.5s ease";
        div.style.opacity    = "0";
        div.style.transform  = "translateX(10px)";
    }, 4500);

    setTimeout(() => div.remove(), 5000);
};


window.apiAction = function ({
    url, method = "POST", body = null,
    msgOk = null, msgError = "Error al realizar la acción.",
    reload = false, reloadDelay = 1200,
    onSuccess = null, onError = null,
    loadingBtn = null
}) {
    if (loadingBtn) {
        loadingBtn.disabled = true;
        loadingBtn._textoOriginal = loadingBtn.innerHTML;
        loadingBtn.innerHTML = '<span class="spinner"></span>';
    }

    const opts = { method };
    if (body) {
        opts.body    = JSON.stringify(body);
    }

    csrfFetch(url, opts)
        .then(r => r.json())
        .then(res => {
            if (loadingBtn) {
                loadingBtn.disabled  = false;
                loadingBtn.innerHTML = loadingBtn._textoOriginal;
            }
            if (res.ok) {
                if (msgOk)    mostrarFeedback(msgOk, "success");
                if (onSuccess) onSuccess(res);
                if (reload)   setTimeout(() => location.reload(), reloadDelay);
            } else {
                mostrarFeedback(res.error || msgError, "error");
                if (onError) onError(res);
            }
        })
        .catch(() => {
            if (loadingBtn) {
                loadingBtn.disabled  = false;
                loadingBtn.innerHTML = loadingBtn._textoOriginal;
            }
            mostrarFeedback("Error de conexión.", "error");
        });
};


window.crearEliminarHandler = function (modalId) {
    let _pendingUrl = null;
    return {
        confirmar(url) { _pendingUrl = url; abrirModal(modalId); },
        ejecutar()     { if (_pendingUrl) location.href = _pendingUrl; }
    };
};


window.confirmarEliminarVenta = function (idVenta) {
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
};


document.addEventListener("DOMContentLoaded", () => {
    const alerts = document.querySelectorAll(".alert");

    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease, transform 0.5s ease";
            alert.style.opacity    = "0";
            alert.style.transform  = "translateX(10px)";
        }, 4500);

        setTimeout(() => {
            alert.style.display = "none";
        }, 5000);
    });
});