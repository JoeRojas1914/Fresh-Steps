import { abrirModal } from '../components/modal.js';

const MODAL_ID = "modalSalirSinGuardar";

export function initNavigationGuard(isDirty) {
    let disabled    = false;
    let destino     = null;  
    let guardActive = true;   


    history.pushState({ navigationGuard: true }, "");

    window.addEventListener("popstate", () => {
        if (!guardActive) return;

        if (disabled || !isDirty()) {
            guardActive = false;
            history.back();
            return;
        }

        history.pushState({ navigationGuard: true }, "");
        destino = null;
        abrirModal(MODAL_ID);
    });

    window.addEventListener("beforeunload", e => {
        if (disabled || !isDirty()) return;
        e.preventDefault();
        e.returnValue = "";
    });

    document.addEventListener("click", e => {
        if (disabled) return;
        const link = e.target.closest("a[href]");
        if (!link) return;
        const href = link.getAttribute("href");
        if (!href
            || link.target === "_blank"
            || href.startsWith("#")
            || href.startsWith("javascript:")) return;
        if (!isDirty()) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        destino = href;
        abrirModal(MODAL_ID);
    }, true);

    document.getElementById("btnConfirmarSalir")?.addEventListener("click", () => {
        disabled    = true;
        guardActive = false;
        if (destino) {
            window.location.href = destino;
        } else {
            history.go(-2);
        }
    });

    return () => { disabled = true; guardActive = false; };
}
