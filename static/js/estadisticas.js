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

const redPalette       = ["#7f1d1d","#991b1b","#b91c1c","#dc2626","#ef4444"];
const serviciosPalette = ["#60a5fa","#34d399","#fbbf24","#a78bfa","#fb7185","#38bdf8","#4ade80"];
const negocioPalette   = ["#6366f1","#22c55e","#f59e0b","#ef4444","#3b82f6"];
const pagoPalette      = ["#22c55e","#3b82f6","#f59e0b","#a78bfa","#fb7185"];
const rankColors       = ["#f59e0b","#9ca3af","#b45309","#6366f1","#22c55e"];
const aplicarRojos = ds => ds.map((d,i)=>({...d,backgroundColor:redPalette[i%5],borderColor:"#7f1d1d",borderWidth:1,borderRadius:6}));

let modoActual = "mes";

let gastosChart, ingresosChart, ventasSemanaChart, unidadesSemanaChart,
    tipoPagoChart, serviciosChart, ventasPorDiaChart, ingresosNegocioChart,
    metodosPagoChart, horaPicoRecepcionChart, horaPicoEntregaChart;

const barOpts = (fmtVal=fmtN, horizontal=false) => ({
    responsive: true,
    indexAxis: horizontal ? "y" : "x",
    plugins: { legend:{display:false}, tooltip:{callbacks:{label:c=>` ${fmtVal(c.raw)}`}} },
    scales: { [horizontal?"x":"y"]: { beginAtZero:true, ticks:{precision:0} } }
});

const pieOpts = (label="") => ({
    plugins: {
        legend:{labels:{color:"#0b3c5d"}},
        tooltip:{callbacks:{label:c=>{const t=c.dataset.data.reduce((a,b)=>a+b,0); return ` ${c.label}: ${((c.raw/t)*100).toFixed(1)}% (${fmtN(c.raw)}${label})`}}}
    }
});

function initCharts() {
    gastosChart = new Chart(document.getElementById("gastosChart"),{
        type:"bar",data:{labels:[],datasets:[]},
        options:{responsive:true,plugins:{legend:{display:true},tooltip:{callbacks:{label:c=>` ${c.dataset.label}: ${fmt$(c.raw)}`}}},
            scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true,ticks:{callback:v=>fmt$(v)}}}}
    });
    ingresosChart = new Chart(document.getElementById("ingresosChart"),{
        type:"bar",data:{labels:[],datasets:[{label:"Ingresos",data:[],backgroundColor:"#22c55e",borderColor:"#16a34a",borderWidth:1,borderRadius:8}]},
        options:{responsive:true,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>` ${fmt$(c.raw)}`}}},scales:{y:{beginAtZero:true,ticks:{callback:v=>fmt$(v)}}}}
    });
    ventasSemanaChart = new Chart(document.getElementById("ventasSemanaChart"),{
        type:"bar",data:{labels:[],datasets:[{label:"Ventas",data:[],backgroundColor:"#f59e0b",borderColor:"#b45309",borderWidth:1,borderRadius:8}]},
        options:barOpts()
    });
    unidadesSemanaChart = new Chart(document.getElementById("unidadesSemanaChart"),{
        type:"bar",data:{labels:[],datasets:[{label:"Unidades",data:[],backgroundColor:"#14b8a6",borderColor:"#0f766e",borderWidth:1,borderRadius:8}]},
        options:barOpts()
    });
    tipoPagoChart = new Chart(document.getElementById("tipoPagoChart"),{
        type:"pie",data:{labels:[],datasets:[{data:[],backgroundColor:["#34d399","#fbbf24","#60a5fa"],borderColor:"#fff",borderWidth:2}]},
        options:pieOpts(" ventas")
    });
    metodosPagoChart = new Chart(document.getElementById("metodosPagoChart"),{
        type:"doughnut",data:{labels:[],datasets:[{data:[],backgroundColor:pagoPalette,borderColor:"#fff",borderWidth:2}]},
        options:{plugins:{legend:{labels:{color:"#0b3c5d"}},tooltip:{callbacks:{label:c=>{
            const t=c.dataset.data.reduce((a,b)=>a+b,0);
            return ` ${c.label}: ${((c.raw/t)*100).toFixed(1)}% (${fmtN(c.raw)} pagos)`;
        }}}}}
    });
    serviciosChart = new Chart(document.getElementById("serviciosChart"),{
        type:"bar",data:{labels:[],datasets:[{label:"Usos",data:[],backgroundColor:serviciosPalette,borderColor:"rgba(0,0,0,.1)",borderWidth:1,borderRadius:6}]},
        options:{responsive:true,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>` ${fmtN(c.raw)} usos`}}},scales:{y:{beginAtZero:true}}}
    });
    ventasPorDiaChart = new Chart(document.getElementById("ventasPorDiaChart"),{
        type:"bar",data:{labels:["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"],
            datasets:[{label:"Ventas",data:[0,0,0,0,0,0],backgroundColor:"#6366f1",borderColor:"#4338ca",borderWidth:1,borderRadius:8}]},
        options:barOpts()
    });
    ingresosNegocioChart = new Chart(document.getElementById("ingresosNegocioChart"),{
        type:"pie",data:{labels:[],datasets:[{data:[],backgroundColor:negocioPalette,borderColor:"#fff",borderWidth:2}]},
        options:{plugins:{legend:{labels:{color:"#0b3c5d"}},tooltip:{callbacks:{label:c=>{
            const t=c.dataset.data.reduce((a,b)=>a+b,0);
            return ` ${c.label}: ${((c.raw/t)*100).toFixed(1)}% (${fmt$(c.raw)})`;
        }}}}}
    });

    const horaOpts = titulo => ({
        responsive:true, indexAxis:"y",
        plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>` ${fmtN(c.raw)} ventas`}}},
        scales:{x:{beginAtZero:true,ticks:{precision:0}},y:{ticks:{font:{size:11}}}}
    });
    horaPicoRecepcionChart = new Chart(document.getElementById("horaPicoRecepcionChart"),{
        type:"bar",data:{labels:[],datasets:[{data:[],backgroundColor:"#60a5fa",borderColor:"#2563eb",borderWidth:1,borderRadius:4}]},
        options:horaOpts("recepciones")
    });
    horaPicoEntregaChart = new Chart(document.getElementById("horaPicoEntregaChart"),{
        type:"bar",data:{labels:[],datasets:[{data:[],backgroundColor:"#34d399",borderColor:"#059669",borderWidth:1,borderRadius:4}]},
        options:horaOpts("entregas")
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

function switchTab(nombre, btn) {
    document.querySelectorAll(".tab-panel").forEach(p => p.style.display="none");
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.getElementById(`tab-${nombre}`).style.display="";
    btn.classList.add("active");
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
            const actual   = p.inicio === p.fin
                ? fmtFecha(p.inicio)
                : `${fmtFecha(p.inicio)} – ${fmtFecha(p.fin)}`;
            const anterior = pa.inicio === pa.fin
                ? fmtFecha(pa.inicio)
                : `${fmtFecha(pa.inicio)} – ${fmtFecha(pa.fin)}`;

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
        if (data.gastos_semanales) { gastosChart.data.labels=data.gastos_semanales.labels||[]; gastosChart.data.datasets=aplicarRojos(data.gastos_semanales.datasets||[]); gastosChart.update(); }
        if (data.ventas_semanales) { ventasSemanaChart.data.labels=data.ventas_semanales.map(x=>x.label); ventasSemanaChart.data.datasets[0].data=data.ventas_semanales.map(x=>x.total); ventasSemanaChart.update(); }
        if (data.unidades_semanales) { unidadesSemanaChart.data.labels=data.unidades_semanales.map(x=>x.label); unidadesSemanaChart.data.datasets[0].data=data.unidades_semanales.map(x=>x.total); unidadesSemanaChart.update(); }
        if (data.ventas_prepago) { tipoPagoChart.data.labels=data.ventas_prepago.map(x=>x.tipo); tipoPagoChart.data.datasets[0].data=data.ventas_prepago.map(x=>x.total); tipoPagoChart.update(); }
        if (data.uso_servicios) { serviciosChart.data.labels=data.uso_servicios.map(x=>x.nombre); serviciosChart.data.datasets[0].data=data.uso_servicios.map(x=>x.total); serviciosChart.update(); }
        if (data.ventas_por_dia) { ventasPorDiaChart.data.datasets[0].data=data.ventas_por_dia; ventasPorDiaChart.update(); }

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

function renderTopClientes(clientes) {
    const c = document.getElementById("topClientesContainer");
    if (!c) return;
    if (!clientes.length) {
        c.innerHTML = '<p style="opacity:.5;text-align:center;padding:2rem;">Sin datos para este período.</p>';
        return;
    }
    const max = clientes[0].visitas || 1;
    c.innerHTML = `
        <table class="top-clientes-table">
            <thead>
                <tr>
                    <th style="background:#1e7fd6;color:#fff;border-radius:8px 0 0 0;">#</th>
                    <th style="background:#1e7fd6;color:#fff;">Cliente</th>
                    <th style="background:#1e7fd6;color:#fff;text-align:center;">Visitas</th>
                    <th style="background:#1e7fd6;color:#fff;text-align:right;">Total gastado</th>
                    <th style="background:#1e7fd6;color:#fff;border-radius:0 8px 0 0;">Frecuencia</th>
                </tr>
            </thead>
            <tbody>
                ${clientes.map((cl, i) => `
                <tr>
                    <td style="width:40px;text-align:center">
                        <span class="rank-badge" style="background:${rankColors[i]}">${i+1}</span>
                    </td>
                    <td style="font-weight:600">${cl.nombre}</td>
                    <td style="text-align:center">${fmtN(cl.visitas)} visita${cl.visitas !== 1 ? "s" : ""}</td>
                    <td style="text-align:right;font-weight:600;color:#22c55e">${fmt$(cl.total_gastado)}</td>
                    <td>
                        <div style="background:#f3f4f6;border-radius:4px;height:8px;overflow:hidden">
                            <div style="background:${rankColors[i]};height:100%;width:${(cl.visitas/max*100).toFixed(0)}%;border-radius:4px;transition:width .4s"></div>
                        </div>
                    </td>
                </tr>`).join("")}
            </tbody>
        </table>`;
}

function setKpi(id,valor,pct) { const el=document.getElementById(id); if(el) el.innerHTML=fmt$(valor)+badgePct(pct); }
function mostrarError(msg) {
    let el=document.getElementById("dashboard-error");
    if (!el) { el=document.createElement("div"); el.id="dashboard-error"; el.style.cssText="background:#fee2e2;color:#b91c1c;padding:10px 16px;border-radius:8px;margin:12px 0;font-size:13px;font-weight:500;"; document.querySelector(".filtro-box").after(el); }
    el.textContent="⚠️ "+msg; el.style.display="block";
}
function ocultarError() { const el=document.getElementById("dashboard-error"); if(el) el.style.display="none"; }
function verVentasRelacionadas() {
    const p=getParams(); if(!p) return;
    const params=new URLSearchParams({fecha_inicio:p.inicio,fecha_fin:p.fin});
    if(p.id_negocio!=="all") params.set("id_negocio",p.id_negocio);
    window.open(`/ventas/historial?${params.toString()}`,"_blank");
}

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