// ── Formatters ───────────────────────────────────────────────────────────────
const fmt$ = n => "$" + Number(n||0).toLocaleString("es-MX",{minimumFractionDigits:2,maximumFractionDigits:2});
const fmtN = n => Number(n||0).toLocaleString("es-MX");
const fmtFecha = iso => {
    const [y,m,d] = iso.split("-");
    const M = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
    return `${parseInt(d)} ${M[parseInt(m)-1]} ${y}`;
};
const badgePct = pct => {
    if (pct===null||pct===undefined) return "";
    const c = pct>=0?"#22c55e":"#ef4444";
    return `<span style="font-size:12px;font-weight:600;color:${c};margin-left:6px">${pct>=0?"↑":"↓"} ${Math.abs(pct).toFixed(1)}%</span>`;
};

// ── Color palettes ────────────────────────────────────────────────────────────
const redPalette       = ["#7f1d1d","#991b1b","#b91c1c","#dc2626","#ef4444"];
const serviciosPalette = ["#60a5fa","#34d399","#fbbf24","#a78bfa","#fb7185","#38bdf8","#4ade80"];
const negocioPalette   = ["#6366f1","#22c55e","#f59e0b","#ef4444","#3b82f6"];
const pagoPalette      = ["#22c55e","#3b82f6","#f59e0b","#a78bfa","#fb7185"];
const rankColors       = ["#f59e0b","#9ca3af","#b45309","#6366f1","#22c55e"];
const aplicarRojos = ds => ds.map((d,i) => ({
    ...d,
    backgroundColor: redPalette[i%5],
    borderColor: "transparent",
    borderWidth: 0,
    borderRadius: 6,
    borderSkipped: false
}));

Chart.defaults.font.family = "'Inter', 'Segoe UI', sans-serif";
Chart.defaults.font.size   = 12;
Chart.defaults.color       = '#64748b';
Chart.defaults.borderColor = 'rgba(226, 232, 240, 0.6)';


Chart.register({
    id: 'gradientBg',
    beforeDatasetsDraw(chart) {
        chart.data.datasets.forEach((ds, i) => {
            if (!ds._gradient) return;
            const { ctx, chartArea, canvas } = chart;
            const top    = chartArea ? chartArea.top    : 0;
            const bottom = chartArea ? chartArea.bottom : canvas.height;
            if (bottom === 0) return;
            const g = ctx.createLinearGradient(0, top, 0, bottom);
            g.addColorStop(0, ds._gradient[0]);
            g.addColorStop(1, ds._gradient[1]);
            chart.data.datasets[i].backgroundColor = g;
        });
    }
});

const tooltipStyle = {
    backgroundColor: '#ffffff',
    titleColor: '#0f172a',
    bodyColor: '#475569',
    borderColor: '#e2e8f0',
    borderWidth: 1,
    cornerRadius: 10,
    padding: 12,
    titleFont: { weight: '700', size: 13 },
    bodyFont: { size: 12 },
};

const gridSoft = { color: 'rgba(226,232,240,0.5)' };
const gridNone = { display: false };
const noBorder = { display: false };

const legendBottom = { position: 'bottom', labels: { color: '#1e293b', padding: 16, font: { size: 12 } } };

const barOpts = (fmtVal=fmtN, horizontal=false) => ({
    responsive: true,
    indexAxis: horizontal ? "y" : "x",
    plugins: {
        legend: { display: false },
        tooltip: { ...tooltipStyle, callbacks: { label: c => ` ${fmtVal(c.raw)}` } }
    },
    scales: horizontal ? {
        x: { beginAtZero: true, ticks: { precision: 0 }, grid: gridSoft, border: noBorder },
        y: { grid: gridNone, border: noBorder }
    } : {
        y: { beginAtZero: true, ticks: { precision: 0 }, grid: gridSoft, border: noBorder },
        x: { grid: gridNone, border: noBorder }
    }
});

const pieOpts = (label="") => ({
    plugins: {
        legend: legendBottom,
        tooltip: {
            ...tooltipStyle,
            callbacks: {
                label: c => {
                    const t = c.dataset.data.reduce((a,b) => a+b, 0);
                    return ` ${c.label}: ${((c.raw/t)*100).toFixed(1)}% (${fmtN(c.raw)}${label})`;
                }
            }
        }
    },
    hoverOffset: 10
});

let modoActual = "mes";

let gastosChart, ingresosChart, ventasSemanaChart, unidadesSemanaChart,
    tipoPagoChart, serviciosChart, ventasPorDiaChart, ingresosNegocioChart,
    metodosPagoChart, horaPicoRecepcionChart, horaPicoEntregaChart;

function initCharts() {

    gastosChart = new Chart(document.getElementById("gastosChart"), {
        type: "bar",
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true, ...legendBottom },
                tooltip: { ...tooltipStyle, callbacks: { label: c => ` ${c.dataset.label}: ${fmt$(c.raw)}` } }
            },
            scales: {
                x: { stacked: true, grid: gridNone, border: noBorder },
                y: { stacked: true, beginAtZero: true, ticks: { callback: v => fmt$(v) }, grid: gridSoft, border: noBorder }
            }
        }
    });

    ingresosChart = new Chart(document.getElementById("ingresosChart"), {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Ingresos",
                data: [],
                borderColor: '#22c55e',
                borderWidth: 2.5,
                _gradient: ['rgba(34,197,94,0.30)', 'rgba(34,197,94,0)'],
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#22c55e',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 7,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: { ...tooltipStyle, callbacks: { label: c => ` ${fmt$(c.raw)}` } }
            },
            scales: {
                y: { beginAtZero: true, ticks: { callback: v => fmt$(v) }, grid: gridSoft, border: noBorder },
                x: { grid: gridNone, border: noBorder }
            }
        }
    });

    ventasSemanaChart = new Chart(document.getElementById("ventasSemanaChart"), {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Ventas",
                data: [],
                borderColor: '#f59e0b',
                borderWidth: 2.5,
                _gradient: ['rgba(245,158,11,0.30)', 'rgba(245,158,11,0)'],
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#f59e0b',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 7,
            }]
        },
        options: barOpts()
    });

    unidadesSemanaChart = new Chart(document.getElementById("unidadesSemanaChart"), {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Unidades",
                data: [],
                borderColor: '#14b8a6',
                borderWidth: 2.5,
                _gradient: ['rgba(20,184,166,0.30)', 'rgba(20,184,166,0)'],
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#14b8a6',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 7,
            }]
        },
        options: barOpts()
    });

    tipoPagoChart = new Chart(document.getElementById("tipoPagoChart"), {
        type: "pie",
        data: {
            labels: [],
            datasets: [{ data: [], backgroundColor: ["#34d399","#fbbf24","#60a5fa"], borderColor: "#fff", borderWidth: 3 }]
        },
        options: pieOpts(" ventas")
    });

    metodosPagoChart = new Chart(document.getElementById("metodosPagoChart"), {
        type: "doughnut",
        data: {
            labels: [],
            datasets: [{ data: [], backgroundColor: pagoPalette, borderColor: "#fff", borderWidth: 3 }]
        },
        options: {
            cutout: '62%',
            plugins: {
                legend: legendBottom,
                tooltip: {
                    ...tooltipStyle,
                    callbacks: {
                        label: c => {
                            const t = c.dataset.data.reduce((a,b) => a+b, 0);
                            return ` ${c.label}: ${((c.raw/t)*100).toFixed(1)}% (${fmtN(c.raw)} pagos)`;
                        }
                    }
                }
            },
            hoverOffset: 10
        }
    });

    serviciosChart = new Chart(document.getElementById("serviciosChart"), {
        type: "bar",
        data: {
            labels: [],
            datasets: [{
                label: "Usos",
                data: [],
                backgroundColor: serviciosPalette,
                borderWidth: 0,
                borderRadius: 8,
                borderSkipped: false,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: { ...tooltipStyle, callbacks: { label: c => ` ${fmtN(c.raw)} usos` } }
            },
            scales: {
                y: { beginAtZero: true, grid: gridSoft, border: noBorder },
                x: { grid: gridNone, border: noBorder }
            }
        }
    });

    ventasPorDiaChart = new Chart(document.getElementById("ventasPorDiaChart"), {
        type: "line",
        data: {
            labels: ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"],
            datasets: [{
                label: "Ventas",
                data: [0,0,0,0,0,0],
                borderColor: '#6366f1',
                borderWidth: 2.5,
                _gradient: ['rgba(99,102,241,0.30)', 'rgba(99,102,241,0)'],
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#6366f1',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 7,
            }]
        },
        options: barOpts()
    });

    ingresosNegocioChart = new Chart(document.getElementById("ingresosNegocioChart"), {
        type: "pie",
        data: {
            labels: [],
            datasets: [{ data: [], backgroundColor: negocioPalette, borderColor: "#fff", borderWidth: 3 }]
        },
        options: {
            plugins: {
                legend: legendBottom,
                tooltip: {
                    ...tooltipStyle,
                    callbacks: {
                        label: c => {
                            const t = c.dataset.data.reduce((a,b) => a+b, 0);
                            return ` ${c.label}: ${((c.raw/t)*100).toFixed(1)}% (${fmt$(c.raw)})`;
                        }
                    }
                }
            },
            hoverOffset: 10
        }
    });

    const horaOpts = (labelSuffix) => ({
        responsive: true,
        indexAxis: "y",
        plugins: {
            legend: { display: false },
            tooltip: { ...tooltipStyle, callbacks: { label: c => ` ${fmtN(c.raw)} ${labelSuffix}` } }
        },
        scales: {
            x: { beginAtZero: true, ticks: { precision: 0 }, grid: gridSoft, border: noBorder },
            y: { grid: gridNone, border: noBorder, ticks: { font: { size: 11 } } }
        }
    });

    horaPicoRecepcionChart = new Chart(document.getElementById("horaPicoRecepcionChart"), {
        type: "bar",
        data: {
            labels: [],
            datasets: [{
                data: [],
                _gradient: ['rgba(96,165,250,0.85)', 'rgba(96,165,250,0.18)'],
                backgroundColor: 'rgba(96,165,250,0.75)',
                borderWidth: 0,
                borderRadius: 6,
                borderSkipped: false,
            }]
        },
        options: horaOpts("recepciones")
    });

    horaPicoEntregaChart = new Chart(document.getElementById("horaPicoEntregaChart"), {
        type: "bar",
        data: {
            labels: [],
            datasets: [{
                data: [],
                _gradient: ['rgba(52,211,153,0.85)', 'rgba(52,211,153,0.18)'],
                backgroundColor: 'rgba(52,211,153,0.75)',
                borderWidth: 0,
                borderRadius: 6,
                borderSkipped: false,
            }]
        },
        options: horaOpts("entregas")
    });
}

function setModo(modo, btn) {
    modoActual = modo;
    document.querySelectorAll(".modo-panel").forEach(p => p.style.display="none");
    document.querySelectorAll(".modo-btn").forEach(b => b.classList.remove("active"));
    document.getElementById(`panel-${modo}`).style.display = "";
    if (btn) btn.classList.add("active");

    const hoy = new Date();
    const pad = n => String(n).padStart(2,"0");
    if (modo==="dia") {
        document.getElementById("fecha-dia").value = hoy.toISOString().split("T")[0];
    } else if (modo==="semana") {
        const d = new Date(hoy); d.setDate(hoy.getDate()-((hoy.getDay()||7)-1));
        const dif = d - new Date(d.getFullYear(),0,1);
        const w = Math.ceil((dif/86400000 + new Date(d.getFullYear(),0,1).getDay()+1)/7);
        document.getElementById("fecha-semana").value = `${d.getFullYear()}-W${pad(w)}`;
    } else if (modo==="mes") {
        document.getElementById("fecha-mes").value = `${hoy.getFullYear()}-${pad(hoy.getMonth()+1)}`;
    }

    const cardDia = document.getElementById("card-ventas-por-dia");
    if (cardDia) cardDia.style.display = modo==="dia" ? "none" : "";

    cargarDashboard();
}

function getParams() {
    const neg = id => document.getElementById(id)?.value || "all";
    if (modoActual==="dia") {
        const f = document.getElementById("fecha-dia").value;
        return {inicio:f, fin:f, id_negocio:neg("negocio-dia")};
    }
    if (modoActual==="semana") {
        const val = document.getElementById("fecha-semana").value;
        if (!val) return null;
        const [y,w] = val.split("-W");
        const d = new Date(parseInt(y),0,1+(parseInt(w)-1)*7);
        d.setDate(d.getDate()-((d.getDay()||7)-1));
        const fin = new Date(d); fin.setDate(d.getDate()+6);
        const iso = dd => dd.toISOString().split("T")[0];
        return {inicio:iso(d), fin:iso(fin), id_negocio:neg("negocio-semana")};
    }
    if (modoActual==="mes") {
        const val = document.getElementById("fecha-mes").value;
        if (!val) return null;
        const [y,m] = val.split("-");
        const ultimo = new Date(parseInt(y),parseInt(m),0).getDate();
        return {inicio:`${y}-${m}-01`, fin:`${y}-${m}-${String(ultimo).padStart(2,"0")}`, id_negocio:neg("negocio-mes")};
    }
    if (modoActual==="personalizado") {
        return {inicio:document.getElementById("fecha-inicio-custom").value, fin:document.getElementById("fecha-fin-custom").value, id_negocio:neg("negocio-custom")};
    }
    return null;
}

function actualizarTitulos() {
    const sufijos = {dia:"del día", semana:"de la semana", mes:"por semana", personalizado:"por semana"};
    const s = sufijos[modoActual] || "por semana";
    [["titulo-ingresos","Ingresos"],["titulo-gastos","Gastos"],["titulo-ventas","Número de ventas"],["titulo-unidades","Unidades recibidas"]]
        .forEach(([id,base]) => { const el=document.getElementById(id); if(el) el.textContent=`${base} ${s}`; });
}

const chartsPerTab = {
    financiero:  () => [ingresosChart, gastosChart, tipoPagoChart, metodosPagoChart, ingresosNegocioChart],
    operacional: () => [ventasSemanaChart, unidadesSemanaChart, ventasPorDiaChart, horaPicoRecepcionChart, horaPicoEntregaChart, serviciosChart],
    clientes:    () => [],
};

function switchTab(nombre, btn) {
    document.querySelectorAll(".tab-panel").forEach(p => p.style.display="none");
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.getElementById(`tab-${nombre}`).style.display="";
    btn.classList.add("active");
    // Forzar re-render para que el plugin de gradiente tenga chartArea válido
    (chartsPerTab[nombre]?.() || []).forEach(c => c?.update('none'));
}

async function cargarDashboard() {
    const p = getParams();
    if (!p) return;

    if (p.inicio && p.fin && (new Date(p.fin)-new Date(p.inicio))/86400000 > 186) {
        mostrarError("El rango máximo es 6 meses en modo Personalizado.");
        return;
    }
    ocultarError();
    actualizarTitulos();

    try {
        const url = `/api/estadisticas/dashboard?inicio=${p.inicio}&fin=${p.fin}&id_negocio=${p.id_negocio}`;
        const res = await fetch(url);
        if (!res.ok) { const j=await res.json().catch(()=>({})); mostrarError(j.error||`Error ${res.status}`); return; }
        const data = await res.json();

        if (data.periodo_anterior) {
            const pa = data.periodo_anterior;
            const actual   = p.inicio === p.fin ? fmtFecha(p.inicio) : `${fmtFecha(p.inicio)} – ${fmtFecha(p.fin)}`;
            const anterior = pa.inicio === pa.fin ? fmtFecha(pa.inicio) : `${fmtFecha(pa.inicio)} – ${fmtFecha(pa.fin)}`;

            const elActual   = document.getElementById("comparativaPeriodoActual");
            const elAnterior = document.getElementById("comparativaPeriodoAnterior");
            const elNota     = document.getElementById("comparativaNota");
            const elBox      = document.getElementById("comparativaBox");

            if (elActual)   elActual.textContent   = actual;
            if (elAnterior) elAnterior.textContent = anterior;
            if (elNota)     elNota.textContent     = "Los % ↑↓ de los KPIs se calculan contra este período";
            if (elBox)      elBox.style.display    = "flex";
        }

        const k = data.kpis||{};
        setKpi("ventasMes",     k.ingresos,        k.ingresos_pct);
        setKpi("gastosMes",     k.gastos,           k.gastos_pct);
        setKpi("gananciaMes",   k.ganancia,         k.ganancia_pct);
        setKpi("ticketPromedio",k.ticket_promedio,  k.ticket_pct);
        setKpi("saldoCobrar",   k.saldo_por_cobrar, k.saldo_pct);
        const elT=document.getElementById("totalVentas"); if(elT) elT.innerHTML=fmtN(k.total_ventas)+badgePct(k.ventas_pct);
        const elV=document.getElementById("ticketVentas"); if(elV) elV.textContent=`${fmtN(k.num_ventas)} ventas`;

        if (data.ingresos_semanales) { ingresosChart.data.labels=data.ingresos_semanales.map(x=>x.label); ingresosChart.data.datasets[0].data=data.ingresos_semanales.map(x=>x.total); ingresosChart.update(); }
        if (data.gastos_semanales)   { gastosChart.data.labels=data.gastos_semanales.labels||[]; gastosChart.data.datasets=aplicarRojos(data.gastos_semanales.datasets||[]); gastosChart.update(); }
        if (data.ventas_semanales)   { ventasSemanaChart.data.labels=data.ventas_semanales.map(x=>x.label); ventasSemanaChart.data.datasets[0].data=data.ventas_semanales.map(x=>x.total); ventasSemanaChart.update(); }
        if (data.unidades_semanales) { unidadesSemanaChart.data.labels=data.unidades_semanales.map(x=>x.label); unidadesSemanaChart.data.datasets[0].data=data.unidades_semanales.map(x=>x.total); unidadesSemanaChart.update(); }
        if (data.ventas_prepago)     { tipoPagoChart.data.labels=data.ventas_prepago.map(x=>x.tipo); tipoPagoChart.data.datasets[0].data=data.ventas_prepago.map(x=>x.total); tipoPagoChart.update(); }
        if (data.uso_servicios)      { serviciosChart.data.labels=data.uso_servicios.map(x=>x.nombre); serviciosChart.data.datasets[0].data=data.uso_servicios.map(x=>x.total); serviciosChart.update(); }
        if (data.ventas_por_dia)     { ventasPorDiaChart.data.datasets[0].data=data.ventas_por_dia; ventasPorDiaChart.update(); }

        if (data.metodos_pago) {
            metodosPagoChart.data.labels=data.metodos_pago.map(x=>x.metodo);
            metodosPagoChart.data.datasets[0].data=data.metodos_pago.map(x=>x.total);
            metodosPagoChart.update();
        }

        if (data.hora_recepcion) { horaPicoRecepcionChart.data.labels=data.hora_recepcion.map(x=>x.hora); horaPicoRecepcionChart.data.datasets[0].data=data.hora_recepcion.map(x=>x.total); horaPicoRecepcionChart.update(); }
        if (data.hora_entrega)   { horaPicoEntregaChart.data.labels=data.hora_entrega.map(x=>x.hora); horaPicoEntregaChart.data.datasets[0].data=data.hora_entrega.map(x=>x.total); horaPicoEntregaChart.update(); }

        const cardN=document.getElementById("card-ingresos-negocio");
        if (data.ingresos_x_negocio?.length>0) {
            ingresosNegocioChart.data.labels=data.ingresos_x_negocio.map(x=>x.nombre);
            ingresosNegocioChart.data.datasets[0].data=data.ingresos_x_negocio.map(x=>x.total);
            ingresosNegocioChart.update();
            if(cardN) cardN.style.display="";
        } else { if(cardN) cardN.style.display="none"; }

        const elCU = document.getElementById("clientesUnicos");
        if (elCU && data.clientes_unicos !== undefined) elCU.textContent = fmtN(data.clientes_unicos);

        const elCN = document.getElementById("clientesNuevos");
        if (elCN && data.clientes_nuevos !== undefined) elCN.textContent = fmtN(data.clientes_nuevos);

        if (data.tasa_retorno) {
            const elTR  = document.getElementById("tasaRetorno");
            const elSub = document.getElementById("tasaRetornoSub");
            if (elTR)  elTR.textContent  = `${data.tasa_retorno.tasa}%`;
            if (elSub) elSub.textContent = `${fmtN(data.tasa_retorno.recurrentes)} de ${fmtN(data.tasa_retorno.total)} clientes`;
        }

        const elGP = document.getElementById("gastoPorCliente");
        if (elGP && data.gasto_prom_cliente !== undefined) elGP.textContent = fmt$(data.gasto_prom_cliente);

        renderTopClientes(data.top_clientes||[]);

    } catch(err) { mostrarError("Error inesperado al cargar el dashboard."); }
}

const rankMedal = [
    'linear-gradient(135deg,#f59e0b,#d97706)',
    'linear-gradient(135deg,#94a3b8,#64748b)',
    'linear-gradient(135deg,#cd7f32,#92400e)',
    '#e2e8f0',
    '#e2e8f0',
];
const rankTextColor = ['#fff','#fff','#fff','#64748b','#64748b'];
const avatarColors  = ['#dbeafe','#dcfce7','#fef3c7','#ede9fe','#fce7f3'];
const avatarText    = ['#1e40af','#166534','#92400e','#5b21b6','#9d174d'];

function renderTopClientes(clientes) {
    const c = document.getElementById("topClientesContainer");
    if (!c) return;
    if (!clientes.length) {
        c.innerHTML = '<div class="tc-empty">Sin datos para este período.</div>';
        return;
    }
    const maxVisitas   = clientes[0].visitas      || 1;
    const maxGastado   = clientes[0].total_gastado || 1;

    c.innerHTML = `<div class="tc-list">${clientes.map((cl, i) => {
        const initials  = cl.nombre.split(' ').slice(0,2).map(w => w[0]?.toUpperCase() || '').join('');
        const barPct    = ((cl.visitas / maxVisitas) * 100).toFixed(0);
        const montoPct  = ((cl.total_gastado / maxGastado) * 100).toFixed(0);
        return `
        <div class="tc-item">
            <div class="tc-rank" style="background:${rankMedal[i]};color:${rankTextColor[i]}">${i+1}</div>
            <div class="tc-avatar" style="background:${avatarColors[i]};color:${avatarText[i]}">${initials}</div>
            <div class="tc-body">
                <div class="tc-name">${cl.nombre}</div>
                <div class="tc-bar-wrap">
                    <div class="tc-bar" style="width:${barPct}%;background:${rankColors[i]}"></div>
                </div>
            </div>
            <div class="tc-meta">
                <div class="tc-monto">${fmt$(cl.total_gastado)}</div>
                <div class="tc-visitas">${fmtN(cl.visitas)} visita${cl.visitas !== 1 ? 's' : ''}</div>
            </div>
        </div>`;
    }).join('')}</div>`;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function setKpi(id,valor,pct) { const el=document.getElementById(id); if(el) el.innerHTML=fmt$(valor)+badgePct(pct); }
function mostrarError(msg) {
    let el=document.getElementById("dashboard-error");
    if (!el) { el=document.createElement("div"); el.id="dashboard-error"; el.style.cssText="background:#fee2e2;color:#b91c1c;padding:10px 16px;border-radius:8px;margin:12px 0;font-size:13px;font-weight:500;"; document.querySelector(".filtro-box").after(el); }
    el.textContent=msg; el.style.display="block";
}
function ocultarError() { const el=document.getElementById("dashboard-error"); if(el) el.style.display="none"; }
function verVentasRelacionadas() {
    const p=getParams(); if(!p) return;
    const params=new URLSearchParams({fecha_inicio:p.inicio,fecha_fin:p.fin});
    if(p.id_negocio!=="all") params.set("id_negocio",p.id_negocio);
    window.open(`/ventas/historial?${params.toString()}`,"_blank");
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    initCharts();

    const inputs = [
        "fecha-dia", "fecha-semana", "fecha-mes",
        "fecha-inicio-custom", "fecha-fin-custom",
        "negocio-dia", "negocio-semana", "negocio-mes", "negocio-custom"
    ];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener("change", cargarDashboard);
    });

    cargarDashboard();
});
