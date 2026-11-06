import { escapeHtml } from '../base/helpers.js';


let _abort = null;

export async function fetchClientes(q, lista) {
    if (_abort) _abort.abort();
    _abort = new AbortController();

    let clientes;
    try {
        const res = await fetch(`/api/clientes?q=${encodeURIComponent(q)}`, { signal: _abort.signal });
        if (!res.ok) throw new Error("Error de red");
        clientes = await res.json();
    } catch (err) {
        if (err.name === "AbortError") return null;
        lista.innerHTML = "<div class='result-item'>Error al buscar clientes.</div>";
        return null;
    }

    if (clientes.length === 0) {
        lista.innerHTML = `
            <div class="no-clientes-found">
                <i data-lucide="user-x" width="28" height="28"></i>
                <p>No se encontraron clientes con "<strong>${escapeHtml(q)}</strong>"</p>
            </div>`;
        if (window.lucide) lucide.createIcons();
        return null;
    }
    return clientes;
}
