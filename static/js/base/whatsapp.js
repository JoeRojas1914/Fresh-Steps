import { csrfFetch } from './helpers.js';

function formatWaPhone(phone) {
    const digits = phone.replace(/\D/g, '');
    if (digits.startsWith('521') && digits.length === 13) return digits;
    if (digits.startsWith('52')  && digits.length === 12) return '521' + digits.slice(2);
    return '521' + digits.slice(-10);
}

export async function abrirWhatsApp(phone, message, negocioId) {
    const wa  = formatWaPhone(phone);
    const enc = encodeURIComponent(message);
    const url = `https://web.whatsapp.com/send?phone=${wa}&text=${enc}`;

    try {
        const r   = await csrfFetch('/ventas/abrir-whatsapp', {
            method: 'POST',
            body:   JSON.stringify({ url, negocio_id: negocioId }),
        });
        const res = await r.json();
        if (!res.ok) console.error('abrir-whatsapp:', res.error);
        return res;
    } catch (err) {
        console.error('abrir-whatsapp fetch error:', err);
        return { ok: false };
    }
}
