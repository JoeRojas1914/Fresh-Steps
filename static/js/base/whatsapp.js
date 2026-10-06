import { csrfFetch } from './helpers.js';

function formatWaPhone(phone) {
    const digits = phone.replace(/\D/g, '');
    if (digits.startsWith('521') && digits.length === 13) return digits;
    if (digits.startsWith('52')  && digits.length === 12) return '521' + digits.slice(2);
    return '521' + digits.slice(-10);
}

function esAccesoLocal() {
    return ['localhost', '127.0.0.1', '::1', '[::1]'].includes(location.hostname);
}

// Debe llamarse de forma síncrona dentro del click: si se abre después de un
// fetch, el navegador lo bloquea como popup. En acceso local no hace falta,
// el servidor abre el navegador directamente.
export function preabrirVentanaWhatsApp() {
    if (esAccesoLocal()) return null;
    const win = window.open('', '_blank');
    if (win) {
        try { win.document.title = 'Abriendo WhatsApp...'; win.document.body.textContent = 'Abriendo WhatsApp...'; } catch {}
    }
    return win;
}

export function cerrarVentanaPrevia(win) {
    if (win && !win.closed) win.close();
}

export async function abrirWhatsApp(phone, message, negocioId, ventanaPrevia = null) {
    const wa  = formatWaPhone(phone);
    const enc = encodeURIComponent(message);
    const url = `https://web.whatsapp.com/send?phone=${wa}&text=${enc}`;

    try {
        const r   = await csrfFetch('/ventas/abrir-whatsapp', {
            method: 'POST',
            body:   JSON.stringify({ url, negocio_id: negocioId }),
        });
        const res = await r.json();
        if (!res.ok) {
            console.error('abrir-whatsapp:', res.error);
            cerrarVentanaPrevia(ventanaPrevia);
        } else if (!res.opened && res.url) {
            if (ventanaPrevia && !ventanaPrevia.closed) {
                ventanaPrevia.location.href = res.url;
            } else {
                window.open(res.url, '_blank');
            }
        } else {
            cerrarVentanaPrevia(ventanaPrevia);
        }
        return res;
    } catch (err) {
        console.error('abrir-whatsapp fetch error:', err);
        cerrarVentanaPrevia(ventanaPrevia);
        return { ok: false };
    }
}
