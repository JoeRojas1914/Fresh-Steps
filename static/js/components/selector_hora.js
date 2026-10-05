const INTERVALO_MIN = 30;
const APERTURA      = 9 * 60;   
const CIERRE        = 19 * 60;  
const CIERRE_SABADO = 14 * 60;  

function _aMinutos(hhmm) {
    const [h, m] = hhmm.split(":").map(Number);
    return h * 60 + m;
}

function _valor(min) {
    return `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;
}

function _etiqueta(min) {
    const h  = Math.floor(min / 60);
    const h12 = h % 12 || 12;
    return `${h12}:${String(min % 60).padStart(2, "0")} ${h < 12 ? "a.m." : "p.m."}`;
}

function _esSabado(fechaStr) {
    if (!fechaStr) return false;
    const [y, m, d] = fechaStr.split("-").map(Number);
    return new Date(y, m - 1, d).getDay() === 6;
}


export function initSelectorHora(select, valorInicial = "") {
    const opciones = ['<option value="">-- Selecciona --</option>'];
    for (let min = APERTURA; min <= CIERRE; min += INTERVALO_MIN) {
        opciones.push(`<option value="${_valor(min)}">${_etiqueta(min)}</option>`);
    }
    select.innerHTML = opciones.join("");

    if (valorInicial) {
        if (![...select.options].some(o => o.value === valorInicial)) {
            const min = _aMinutos(valorInicial);
            const opt = new Option(_etiqueta(min), valorInicial);
            const siguiente = [...select.options].find(o => o.value && _aMinutos(o.value) > min);
            select.add(opt, siguiente || null);
        }
        select.value = valorInicial;
    }
}

export function ajustarHorasPorFecha(select, fechaStr) {
    const sabado = _esSabado(fechaStr);
    for (const opt of select.options) {
        if (!opt.value) continue;
        opt.disabled = sabado && _aMinutos(opt.value) > CIERRE_SABADO;
    }
    if (select.selectedOptions[0]?.disabled) {
        select.value = "";
        return true;
    }
    return false;
}
