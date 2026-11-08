import { escapeHtml, countUp } from '../base/helpers.js';

// ── Formatters ───────────────────────────────────────────────────────────────
const fmt$ = n => "$" + Number(n||0).toLocaleString("es-MX",{minimumFractionDigits:2,maximumFractionDigits:2});
const fmtN = n => Number(n||0).toLocaleString("es-MX");
const fmtPct = n => `${Number(n||0).toLocaleString("es-MX",{maximumFractionDigits:1})}%`;
const MESES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
const fmtFecha = iso => {
    const [y,m,d] = iso.split("-");
    return `${parseInt(d)} ${MESES[parseInt(m)-1]} ${y}`;
};
// "1 – 5 nov 2026" cuando comparten mes y año; si no, ambas fechas completas
const fmtRango = (ini, fin) => {
    if (ini === fin) return fmtFecha(ini);
    const [y1,m1] = ini.split("-"), [y2,m2] = fin.split("-");
    if (y1 === y2 && m1 === m2) return `${parseInt(ini.split("-")[2])} – ${fmtFecha(fin)}`;
    return `${fmtFecha(ini)} – ${fmtFecha(fin)}`;
};
const badgePct = (pct, invert=false) => {
    if (pct===null||pct===undefined) return `<span class="badge-pct badge-pct--na">sin datos previos</span>`;
    if (pct === 0) return `<span class="badge-pct badge-pct--igual">= 0%</span>`;
    const bueno = invert ? pct < 0 : pct > 0;
    return `<span class="badge-pct ${bueno ? 'badge-pct--ok' : 'badge-pct--mal'}">${pct>0?"↑":"↓"} ${Math.abs(pct).toFixed(1)}%</span>`;
};

// ── Paleta fija (colores de la app) ──────────────────────────────────────────
const C = {
    azul:   "#1e7fd6",
    marino: "#0b3c5d",
    verde:  "#15803d",
    rojo:   "#dc2626",
    ambar:  "#b45309",
    gris:   "#94a3b8",
};
// Mismos colores que los badges .negocio-* (components/badges.css)
const COLOR_NEGOCIO = { 1: "#1e7fd6", 2: "#c44569", 3: "#1a7a87" };
// Gastos apilados: tonos de rojo, del más fuerte al más claro
const ROJOS = ["#991b1b", "#dc2626", "#ef4444", "#f87171", "#fca5a5", "#fecaca"];

Chart.defaults.font.family = "'Inter', 'Segoe UI', sans-serif";
Chart.defaults.font.size   = 12;
Chart.defaults.color       = '#64748b';
Chart.defaults.borderColor = 'rgba(226, 232, 240, 0.7)';
Chart.defaults.maintainAspectRatio = false;

const tooltipStyle = {
    backgroundColor: '#ffffff',
    titleColor: '#0f172a',
    bodyColor: '#475569',
    borderColor: '#e2e8f0',
    borderWidth: 1,
    cornerRadius: 8,
    padding: 10,
    titleFont: { weight: '600', size: 13 },
    bodyFont: { size: 12 },
};

const gridSoft = { color: 'rgba(226,232,240,0.7)' };
const gridNone = { display: false };
const noBorder = { display: false };
const legendTop = { position: 'top', align: 'end', labels: { color: '#334155', boxWidth: 12, boxHeight: 12, padding: 14, font: { size: 12 } } };

// Barras verticales de una serie en el tiempo (cobrado, ventas, unidades)
const barrasVOpts = (fmtVal=fmtN) => ({
    responsive: true,
    plugins: {
        legend: { display: false },
        tooltip: { ...tooltipStyle, callbacks: { label: c => ` ${fmtVal(c.raw)}` } }
    },
    scales: {
        y: { beginAtZero: true, ticks: { precision: 0, callback: v => fmtVal(v) }, grid: gridSoft, border: noBorder },
        x: { grid: gridNone, border: noBorder }
    }
});

// Barras horizontales con el % del total en el tooltip
const barrasHOpts = (fmtVal=fmtN, unidad="") => ({
    responsive: true,
    indexAxis: "y",
    plugins: {
        legend: { display: false },
        tooltip: {
            ...tooltipStyle,
            callbacks: {
                label: c => {
                    const t = c.dataset.data.reduce((a,b) => a+b, 0) || 1;
                    return ` ${fmtVal(c.raw)}${unidad} · ${fmtPct(c.raw / t * 100)}`;
                }
            }
        }
    },
    scales: {
        x: { beginAtZero: true, ticks: { precision: 0, callback: v => fmtVal(v) }, grid: gridSoft, border: noBorder },
        y: { grid: gridNone, border: noBorder, ticks: { color: '#334155' } }
    }
});

const barraDataset = color => ({
    data: [],
    backgroundColor: color,
    borderWidth: 0,
    borderRadius: 4,
    borderSkipped: false,
    maxBarThickness: 28,
});

// Altura de las gráficas horizontales según cuántas filas tienen
function ajustarAltura(chart, filas) {
    const wrap = chart.canvas.parentElement;
    if (wrap) wrap.style.height = `${Math.max(filas, 1) * 34 + 36}px`;
    chart.resize();
}

let modoActual = "mes";
let agrupacionGastos = "proveedor";

let gastosChart, ingresosChart, ventasSemanaChart, unidadesSemanaChart,
    tipoPagoChart, serviciosChart, ventasPorDiaChart, ingresosNegocioChart,
    metodosPagoChart, horaPicoChart, calzadoMarcasChart, calzadoTiposChart;

function initCharts() {
    const el = id => document.getElementById(id);

    gastosChart = new Chart(el("gastosChart"), {
        type: "bar",
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            plugins: {
                legend: legendTop,
                tooltip: { ...tooltipStyle, callbacks: { label: c => ` ${c.dataset.label}: ${fmt$(c.raw)}` } }
            },
            scales: {
                x: { stacked: true, grid: gridNone, border: noBorder },
                y: { stacked: true, beginAtZero: true, ticks: { callback: v => fmt$(v) }, grid: gridSoft, border: noBorder }
            }
        }
    });

    ingresosChart       = new Chart(el("ingresosChart"),       { type: "bar", data: { labels: [], datasets: [{ ...barraDataset(C.verde),  label: "Cobrado" }] },  options: barrasVOpts(fmt$) });
    ventasSemanaChart   = new Chart(el("ventasSemanaChart"),   { type: "bar", data: { labels: [], datasets: [{ ...barraDataset(C.azul),   label: "Ventas" }] },   options: barrasVOpts() });
    unidadesSemanaChart = new Chart(el("unidadesSemanaChart"), { type: "bar", data: { labels: [], datasets: [{ ...barraDataset(C.marino), label: "Unidades" }] }, options: barrasVOpts() });

    ventasPorDiaChart = new Chart(el("ventasPorDiaChart"), {
        type: "bar",
        data: {
            labels: ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"],
            datasets: [{ ...barraDataset(C.azul), label: "Ventas", data: [0,0,0,0,0,0] }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false }, tooltip: { ...tooltipStyle, callbacks: { label: c => ` ${fmtN(c.raw)} ventas` } } },
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 }, grid: gridSoft, border: noBorder },
                x: { grid: gridNone, border: noBorder }
            }
        }
    });

    ingresosNegocioChart = new Chart(el("ingresosNegocioChart"), { type: "bar", data: { labels: [], datasets: [barraDataset(C.azul)] }, options: barrasHOpts(fmt$) });
    tipoPagoChart        = new Chart(el("tipoPagoChart"),        { type: "bar", data: { labels: [], datasets: [barraDataset(C.azul)] }, options: barrasHOpts(fmtN, " ventas") });
    metodosPagoChart     = new Chart(el("metodosPagoChart"),     { type: "bar", data: { labels: [], datasets: [barraDataset(C.marino)] }, options: barrasHOpts(fmtN, " pagos") });
    serviciosChart       = new Chart(el("serviciosChart"),       { type: "bar", data: { labels: [], datasets: [barraDataset(C.azul)] }, options: barrasHOpts(fmtN, " usos") });
    calzadoMarcasChart   = new Chart(el("calzadoMarcasChart"),   { type: "bar", data: { labels: [], datasets: [barraDataset(C.azul)] }, options: barrasHOpts(fmtN, " artículos") });
    calzadoTiposChart    = new Chart(el("calzadoTiposChart"),    { type: "bar", data: { labels: [], datasets: [barraDataset(C.marino)] }, options: barrasHOpts(fmtN, " artículos") });

    horaPicoChart = new Chart(el("horaPicoChart"), {
        type: "bar",
        data: {
            labels: [],
            datasets: [
                { ...barraDataset(C.azul),   label: "Recepciones", maxBarThickness: 16 },
                { ...barraDataset(C.marino), label: "Entregas",    maxBarThickness: 16 },
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: legendTop,
                tooltip: { ...tooltipStyle, mode: "index", intersect: false, callbacks: { label: c => ` ${c.dataset.label}: ${fmtN(c.raw)}` } }
            },
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 }, grid: gridSoft, border: noBorder },
                x: { grid: gridNone, border: noBorder }
            }
        }
    });
}

// Fecha local en formato YYYY-MM-DD (toISOString usa UTC y de noche adelanta el día)
const pad = n => String(n).padStart(2,"0");
const isoLocal = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;

// Semana ISO 8601 de una fecha → { anio, semana }
function semanaISO(fecha) {
    const d = new Date(Date.UTC(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()));
    const dia = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dia);              // jueves de esa semana
    const inicioAnio = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return { anio: d.getUTCFullYear(), semana: Math.ceil(((d - inicioAnio) / 86400000 + 1) / 7) };
}

// Lunes de la semana ISO indicada
function lunesDeSemanaISO(anio, semana) {
    const cuatroEne = new Date(anio, 0, 4);
    const lunesSem1 = new Date(cuatroEne);
    lunesSem1.setDate(cuatroEne.getDate() - ((cuatroEne.getDay() || 7) - 1));
    const lunes = new Date(lunesSem1);
    lunes.setDate(lunesSem1.getDate() + (semana - 1) * 7);
    return lunes;
}

function setModo(modo, btn) {
    modoActual = modo;
    document.querySelectorAll(".modo-panel").forEach(p => p.classList.toggle("d-none", p.id !== `panel-${modo}`));
    document.querySelectorAll(".modo-btn").forEach(b => {
        const activo = b === btn;
        b.classList.toggle("active", activo);
        b.setAttribute("aria-pressed", activo ? "true" : "false");
    });

    const hoy = new Date();
    if (modo==="dia") {
        document.getElementById("fecha-dia").value = isoLocal(hoy);
    } else if (modo==="semana") {
        const { anio, semana } = semanaISO(hoy);
        document.getElementById("fecha-semana").value = `${anio}-W${pad(semana)}`;
    } else if (modo==="mes") {
        document.getElementById("fecha-mes").value = `${hoy.getFullYear()}-${pad(hoy.getMonth()+1)}`;
    } else if (modo==="anio") {
        document.getElementById("fecha-anio").value = String(hoy.getFullYear());
    }

    const cardDia = document.getElementById("card-ventas-por-dia");
    if (cardDia) cardDia.classList.toggle("d-none", modo === "dia");

    cargarDashboard();
}

function getParams() {
    const neg = id => document.getElementById(id)?.value || "all";
    const modo = modoActual;
    if (modo==="dia") {
        const f = document.getElementById("fecha-dia").value;
        if (!f) return null;
        return {inicio:f, fin:f, id_negocio:neg("negocio-stats"), granularidad:"hora", modo};
    }
    if (modo==="semana") {
        const val = document.getElementById("fecha-semana").value;
        if (!val) return null;
        const [y,w] = val.split("-W");
        const lunes = lunesDeSemanaISO(parseInt(y), parseInt(w));
        const domingo = new Date(lunes); domingo.setDate(lunes.getDate()+6);
        return {inicio:isoLocal(lunes), fin:isoLocal(domingo), id_negocio:neg("negocio-stats"), granularidad:"dia", modo};
    }
    if (modo==="mes") {
        const val = document.getElementById("fecha-mes").value;
        if (!val) return null;
        const [y,m] = val.split("-");
        const ultimo = new Date(parseInt(y),parseInt(m),0).getDate();
        return {inicio:`${y}-${m}-01`, fin:`${y}-${m}-${pad(ultimo)}`, id_negocio:neg("negocio-stats"), granularidad:"semana", modo};
    }
    if (modo==="anio") {
        const y = document.getElementById("fecha-anio").value;
        if (!y) return null;
        return {inicio:`${y}-01-01`, fin:`${y}-12-31`, id_negocio:neg("negocio-stats"), granularidad:"mes", modo};
    }
    if (modo==="personalizado") {
        const inicio = document.getElementById("fecha-inicio-custom").value;
        const fin    = document.getElementById("fecha-fin-custom").value;
        if (!inicio || !fin) return null;
        return {inicio, fin, id_negocio:neg("negocio-stats"), granularidad:"semana", modo};
    }
    return null;
}

function actualizarTitulos() {
    const sufijos = {dia:"por hora", semana:"por día", mes:"por semana", anio:"por mes", personalizado:"por semana"};
    const s = sufijos[modoActual] || "por semana";
    const baseVentas   = "Número de ventas";
    const baseUnidades = "Unidades recibidas";
    [
        ["titulo-ingresos", "Cobrado"],
        ["titulo-gastos",   "Gastos"],
        ["titulo-ventas",   baseVentas],
        ["titulo-unidades", baseUnidades],
    ].forEach(([id,base]) => {
        const el = document.getElementById(id);
        if (!el) return;
        const badge = el.querySelector('.chart-total-badge');
        el.textContent = `${base} ${s}`;
        if (badge) el.appendChild(badge);
    });
}

const chartsPerTab = {
    financiero:  () => [ingresosChart, gastosChart, tipoPagoChart, metodosPagoChart, ingresosNegocioChart],
    operacional: () => [ventasSemanaChart, unidadesSemanaChart, ventasPorDiaChart, horaPicoChart, serviciosChart,
                        calzadoMarcasChart, calzadoTiposChart],
    clientes:    () => [],
};

function switchTab(nombre, btn) {
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.toggle("d-none", p.id !== `tab-${nombre}`));
    document.querySelectorAll(".tab-btn").forEach(b => {
        const activo = b === btn;
        b.classList.toggle("active", activo);
        b.setAttribute("aria-selected", activo ? "true" : "false");
    });
    // Las gráficas creadas dentro de un panel oculto miden 0: hay que redimensionarlas al mostrarlas
    (chartsPerTab[nombre]?.() || []).forEach(c => { if (c) { c.resize(); c.update('none'); } });
}

function setBarrasH(chart, filas, valor, etiqueta, colores) {
    chart.data.labels = filas.map(etiqueta);
    chart.data.datasets[0].data = filas.map(valor);
    if (colores) chart.data.datasets[0].backgroundColor = filas.map(colores);
    ajustarAltura(chart, filas.length);
    chart.update();
}

// Cada carga recibe un número; si llega una respuesta de una carga anterior
// (el usuario cambió filtros mientras tanto) se descarta para no pintar datos viejos.
let _dashSeq = 0;

async function cargarDashboard() {
    const p = getParams();
    if (!p) return;
    const seq = ++_dashSeq;

    if (p.modo === "personalizado" && (new Date(p.fin)-new Date(p.inicio))/86400000 > 186) {
        mostrarError("El rango máximo es 6 meses en modo Personalizado.");
        return;
    }
    ocultarError();
    actualizarTitulos();

    const skeletonTimer = setTimeout(() => document.body.classList.add("stats-cargando"), 150);

    try {
        const qs = new URLSearchParams({
            inicio: p.inicio, fin: p.fin, id_negocio: p.id_negocio,
            granularidad: p.granularidad || "semana",
            agrupacion_gastos: agrupacionGastos, modo: p.modo,
        });
        const res = await fetch(`/api/estadisticas/dashboard?${qs.toString()}`);
        if (seq !== _dashSeq) return;
        if (!res.ok) { const j=await res.json().catch(()=>({})); mostrarError(j.error||`Error ${res.status}`); return; }
        const data = await res.json();
        if (seq !== _dashSeq) return;

        // ── Texto "Comparando X con Y" ──
        const elBox = document.getElementById("comparativaBox");
        if (data.periodo_anterior && elBox) {
            const act = data.periodo_actual || { inicio: p.inicio, fin: p.fin };
            const ant = data.periodo_anterior;
            document.getElementById("comparativaPeriodoActual").textContent   = fmtRango(act.inicio, act.fin);
            document.getElementById("comparativaPeriodoAnterior").textContent = fmtRango(ant.inicio, ant.fin);
            const enCurso = act.fin !== p.fin;
            document.getElementById("comparativaNota").textContent = enCurso
                ? "El periodo va en curso: se compara contra los mismos días del periodo anterior."
                : "";
            elBox.style.display = "flex";
        }

        // ── Cifras ──
        const k = data.kpis||{};
        setKpi("ventasMes",      k.ingresos,         k.ingresos_pct, true);
        setKpi("gastosMes",      k.gastos,           k.gastos_pct,   true, true);
        setKpi("gananciaMes",    k.ganancia,         k.ganancia_pct, true);
        setKpi("ticketPromedio", k.ticket_promedio,  k.ticket_pct,   true);
        setKpi("saldoCobrar",    k.saldo_por_cobrar, undefined,      true);
        setKpi("totalVentas",    k.num_ventas,       k.ventas_pct,   false);

        // ── Series en el tiempo ──
        const setSerie = (chart, serie) => {
            chart.data.labels = serie.map(x => x.label);
            chart.data.datasets[0].data = serie.map(x => x.total);
            chart.update();
        };
        if (data.ingresos_semanales) setSerie(ingresosChart, data.ingresos_semanales);
        if (data.gastos_semanales) {
            gastosChart.data.labels = data.gastos_semanales.labels || [];
            gastosChart.data.datasets = (data.gastos_semanales.datasets || []).map((d, i) => ({
                ...d, backgroundColor: ROJOS[i % ROJOS.length], borderWidth: 0, borderRadius: 4, maxBarThickness: 40,
            }));
            gastosChart.update();
        }
        if (data.ventas_semanales) {
            setSerie(ventasSemanaChart, data.ventas_semanales);
            const el = document.getElementById("total-ventas");
            if (el) el.textContent = `Total: ${fmtN(data.ventas_semanales.reduce((s,x)=>s+x.total,0))}`;
        }
        if (data.unidades_semanales) {
            setSerie(unidadesSemanaChart, data.unidades_semanales);
            const el = document.getElementById("total-unidades");
            if (el) el.textContent = `Total: ${fmtN(data.unidades_semanales.reduce((s,x)=>s+x.total,0))}`;
        }
        if (data.ventas_por_dia) {
            ventasPorDiaChart.data.datasets[0].data = data.ventas_por_dia;
            ventasPorDiaChart.update();
            const el = document.getElementById("total-ventas-dia");
            if (el) el.textContent = `Total: ${fmtN(data.ventas_por_dia.reduce((s,v)=>s+v,0))}`;
        }

        // ── Barras horizontales ──
        if (data.ventas_prepago) setBarrasH(tipoPagoChart, data.ventas_prepago, x => x.total, x => x.tipo);
        if (data.metodos_pago) {
            const cap = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : "Otro";
            setBarrasH(metodosPagoChart, data.metodos_pago, x => x.total, x => cap(x.metodo));
        }
        if (data.uso_servicios) setBarrasH(serviciosChart, data.uso_servicios, x => x.total, x => x.nombre);

        // Calzado: solo con Todos o Calzado y si llegó algo en el periodo
        const cardCalzado = document.getElementById("card-calzado");
        const marcas = data.calzado_marcas || [], tipos = data.calzado_tipos || [];
        if (cardCalzado) cardCalzado.classList.toggle("d-none", !marcas.length && !tipos.length);
        setBarrasH(calzadoMarcasChart, marcas, x => x.total, x => x.nombre);
        setBarrasH(calzadoTiposChart,  tipos,  x => x.total, x => x.nombre);

        const cardN = document.getElementById("card-ingresos-negocio");
        if (data.ingresos_x_negocio?.length > 0) {
            setBarrasH(ingresosNegocioChart, data.ingresos_x_negocio, x => x.total, x => x.nombre,
                       x => COLOR_NEGOCIO[x.id_negocio] || C.gris);
            if (cardN) cardN.classList.remove("d-none");
        } else if (cardN) {
            cardN.classList.add("d-none");
        }

        if (data.hora_recepcion && data.hora_entrega) {
            horaPicoChart.data.labels = data.hora_recepcion.map(x => x.hora);
            horaPicoChart.data.datasets[0].data = data.hora_recepcion.map(x => x.total);
            horaPicoChart.data.datasets[1].data = data.hora_entrega.map(x => x.total);
            horaPicoChart.update();
        }

        // ── Clientes ──
        const elCU = document.getElementById("clientesUnicos");
        if (elCU && data.clientes_unicos !== undefined) countUp(elCU, Number(data.clientes_unicos), false);

        const elCN = document.getElementById("clientesNuevos");
        if (elCN && data.clientes_nuevos !== undefined) countUp(elCN, Number(data.clientes_nuevos), false);

        if (data.tasa_retorno) {
            const elTR  = document.getElementById("tasaRetorno");
            const elSub = document.getElementById("tasaRetornoSub");
            if (elTR)  elTR.textContent = fmtPct(data.tasa_retorno.tasa);
            if (elSub) elSub.textContent = `${fmtN(data.tasa_retorno.recurrentes)} de ${fmtN(data.tasa_retorno.total)} ya habían venido antes`;
        }

        const elGP = document.getElementById("gastoPorCliente");
        if (elGP && data.gasto_prom_cliente !== undefined) countUp(elGP, Number(data.gasto_prom_cliente), true);

        renderTopClientes(data.top_clientes||[]);

    } catch(err) {
        if (seq === _dashSeq) mostrarError("No se pudieron cargar las estadísticas. Revisa tu conexión e intenta de nuevo.");
    }
    finally {
        clearTimeout(skeletonTimer);
        if (seq === _dashSeq) document.body.classList.remove("stats-cargando");
    }
}

function renderTopClientes(clientes) {
    const c = document.getElementById("topClientesContainer");
    if (!c) return;
    if (!clientes.length) {
        c.innerHTML = '<div class="tc-empty">No hay ventas con cliente en este periodo.</div>';
        return;
    }
    const maxMonto = Math.max(...clientes.map(cl => cl.total_gastado)) || 1;

    c.innerHTML = `<ol class="tc-list">${clientes.map((cl, i) => {
        const barPct = ((cl.total_gastado / maxMonto) * 100).toFixed(0);
        return `
        <li class="tc-item">
            <span class="tc-rank">${i + 1}</span>
            <div class="tc-body">
                <div class="tc-name">${escapeHtml(cl.nombre)}</div>
                <div class="tc-bar-wrap"><div class="tc-bar" data-pct="${barPct}"></div></div>
            </div>
            <div class="tc-meta">
                <div class="tc-monto dato-sensible">${fmt$(cl.total_gastado)}</div>
                <div class="tc-visitas">${fmtN(cl.visitas)} visita${cl.visitas !== 1 ? 's' : ''}</div>
            </div>
        </li>`;
    }).join('')}</ol>`;

    c.querySelectorAll(".tc-bar[data-pct]").forEach(bar => { bar.style.width = `${bar.dataset.pct}%`; });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function setKpi(id, valor, pct, monetario, invert=false) {
    const el = document.getElementById(id);
    if (!el) return;
    const badge = pct === undefined ? "" : badgePct(pct, invert);
    el.innerHTML = `<span class="kpi-anim-num"></span>${badge}`;
    countUp(el.querySelector(".kpi-anim-num"), Number(valor || 0), monetario);
}
function mostrarError(msg) {
    let el = document.getElementById("dashboard-error");
    if (!el) {
        el = document.createElement("div");
        el.id = "dashboard-error";
        el.className = "alert error";
        el.setAttribute("role", "alert");
        document.querySelector(".st-filtros").after(el);
    }
    el.textContent = msg;
    el.style.display = "flex";
}
function ocultarError() { const el=document.getElementById("dashboard-error"); if(el) el.style.display="none"; }
function verVentasRelacionadas() {
    const p=getParams(); if(!p) return;
    const params=new URLSearchParams({fecha_inicio:p.inicio,fecha_fin:p.fin});
    if(p.id_negocio!=="all") params.set("id_negocio",p.id_negocio);
    window.open(`/ventas/historial?${params.toString()}`,"_blank");
}

// ── Init ──────────────────────────────────────────────────────────────────────
let _dashTimer = null;
function _cargarDashboardDebounced() {
    clearTimeout(_dashTimer);
    _dashTimer = setTimeout(cargarDashboard, 400);
}

// Montos siempre censurados al entrar; el estado no se guarda entre visitas
function initToggleMontos() {
    const toggleBtn = document.getElementById("toggleMontos");
    if (!toggleBtn) return;
    toggleBtn.addEventListener("click", () => {
        const visible = toggleBtn.getAttribute("aria-pressed") !== "true";
        document.body.classList.toggle("montos-visibles", visible);
        toggleBtn.setAttribute("aria-pressed", visible ? "true" : "false");
        const texto = toggleBtn.querySelector(".st-toggle-texto");
        if (texto) texto.textContent = visible ? "Ocultar montos" : "Mostrar montos";
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    initToggleMontos();

    // Chart.js mide las etiquetas al dibujar; si Inter aún no carga, las corta. Redibujar al cargar.
    document.fonts?.ready.then(() => {
        [gastosChart, ingresosChart, ventasSemanaChart, unidadesSemanaChart, tipoPagoChart, serviciosChart,
         ventasPorDiaChart, ingresosNegocioChart, metodosPagoChart, horaPicoChart,
         calzadoMarcasChart, calzadoTiposChart].forEach(c => c?.update('none'));
    });

    [
        "fecha-dia", "fecha-semana", "fecha-mes", "fecha-anio",
        "fecha-inicio-custom", "fecha-fin-custom",
        "negocio-stats",
    ].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener("change", _cargarDashboardDebounced);
    });

    cargarDashboard();

    document.addEventListener("click", function (e) {
        const btnModo = e.target.closest(".modo-btn[data-modo]");
        if (btnModo) { setModo(btnModo.dataset.modo, btnModo); return; }

        const btnAgrupacion = e.target.closest(".agrupacion-btn[data-agrupacion]");
        if (btnAgrupacion) {
            agrupacionGastos = btnAgrupacion.dataset.agrupacion;
            document.querySelectorAll("#gastos-agrupacion .agrupacion-btn").forEach(b => b.classList.toggle("active", b === btnAgrupacion));
            cargarDashboard();
            return;
        }

        const btnTab = e.target.closest(".tab-btn[data-tab]");
        if (btnTab) { switchTab(btnTab.dataset.tab, btnTab); return; }

        const btnVerVentas = e.target.closest(".js-ver-ventas");
        if (btnVerVentas) { verVentasRelacionadas(); return; }

        const btnExportar = e.target.closest("#btn-exportar-stats");
        if (btnExportar && !btnExportar.dataset.exporting) {
            const p = getParams();
            if (!p || !p.inicio || !p.fin) {
                mostrarError("Elige un periodo antes de exportar.");
                return;
            }
            const params = new URLSearchParams({
                inicio:     p.inicio,
                fin:        p.fin,
                id_negocio: p.id_negocio || "all",
            });

            btnExportar.dataset.exporting = "1";
            const originalHTML = btnExportar.innerHTML;
            btnExportar.innerHTML = '<span class="spinner spinner--sm"></span> Generando...';
            btnExportar.style.pointerEvents = "none";

            window.location.href = `/estadisticas/exportar?${params.toString()}`;

            setTimeout(() => {
                btnExportar.textContent = "Descargado";
                setTimeout(() => {
                    btnExportar.innerHTML = originalHTML;
                    btnExportar.style.pointerEvents = "";
                    delete btnExportar.dataset.exporting;
                    if (window.lucide) lucide.createIcons();
                }, 1200);
            }, 1500);
            return;
        }
    });
});
