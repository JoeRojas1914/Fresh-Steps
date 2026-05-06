const fmt$ = n =>
    "$" + Number(n || 0).toLocaleString("es-MX", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

const fmtN = n => Number(n || 0).toLocaleString("es-MX");

function badgePct(pct) {
    if (pct === null || pct === undefined) return "";
    const abs   = Math.abs(pct).toFixed(1);
    const sube  = pct >= 0;
    const color = sube ? "#22c55e" : "#ef4444";
    const flecha = sube ? "↑" : "↓";
    return `<span style="font-size:12px;font-weight:600;color:${color};margin-left:6px">${flecha} ${abs}%</span>`;
}

const redPalette = ["#7f1d1d","#991b1b","#b91c1c","#dc2626","#ef4444"];
const serviciosPalette = [
    "#60a5fa","#34d399","#fbbf24","#a78bfa",
    "#fb7185","#38bdf8","#4ade80"
];

function aplicarColoresRojos(datasets) {
    return datasets.map((ds, i) => ({
        ...ds,
        backgroundColor: redPalette[i % redPalette.length],
        borderColor: "#7f1d1d",
        borderWidth: 1,
        borderRadius: 6
    }));
}

let gastosChart, ingresosChart, ventasSemanaChart,
    unidadesSemanaChart, tipoPagoChart, serviciosChart, ventasPorDiaChart;

const optsBarBase = (formatearValor = fmtN) => ({
    responsive: true,
    plugins: {
        legend: { display: false },
        tooltip: {
            callbacks: {
                label: ctx => ` ${formatearValor(ctx.raw)}`
            }
        }
    },
    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
});

function initCharts() {
    gastosChart = new Chart(document.getElementById("gastosChart"), {
        type: "bar",
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true,
                    labels: { generateLabels: () => [{
                        text: "Gastos ($)", fillStyle: "#b91c1c",
                        strokeStyle: "#7f1d1d", lineWidth: 1
                    }]}
                },
                tooltip: { callbacks: {
                    label: ctx => ` ${ctx.dataset.label}: ${fmt$(ctx.raw)}`
                }}
            },
            scales: {
                x: { stacked: true },
                y: { stacked: true, beginAtZero: true,
                     ticks: { callback: v => fmt$(v) } }
            }
        }
    });

    ingresosChart = new Chart(document.getElementById("ingresosChart"), {
        type: "bar",
        data: { labels: [], datasets: [{
            label: "Ingresos ($)", data: [],
            backgroundColor: "#22c55e", borderColor: "#16a34a",
            borderWidth: 1, borderRadius: 8
        }]},
        options: {
            ...optsBarBase(fmt$),
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: {
                    label: ctx => ` ${fmt$(ctx.raw)}`
                }}
            },
            scales: { y: { beginAtZero: true,
                ticks: { callback: v => fmt$(v) } } }
        }
    });

    ventasSemanaChart = new Chart(document.getElementById("ventasSemanaChart"), {
        type: "bar",
        data: { labels: [], datasets: [{
            label: "Ventas", data: [],
            backgroundColor: "#f59e0b", borderColor: "#b45309",
            borderWidth: 1, borderRadius: 8
        }]},
        options: optsBarBase()
    });

    unidadesSemanaChart = new Chart(document.getElementById("unidadesSemanaChart"), {
        type: "bar",
        data: { labels: [], datasets: [{
            label: "Unidades", data: [],
            backgroundColor: "#14b8a6", borderColor: "#0f766e",
            borderWidth: 1, borderRadius: 8
        }]},
        options: optsBarBase()
    });

    tipoPagoChart = new Chart(document.getElementById("tipoPagoChart"), {
        type: "pie",
        data: { labels: [], datasets: [{
            data: [],
            backgroundColor: ["#34d399","#fbbf24"],
            borderColor: "#ffffff", borderWidth: 2
        }]},
        options: { plugins: {
            legend: { labels: { color: "#0b3c5d" } },
            tooltip: { callbacks: {
                label: ctx => {
                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                    const pct   = ((ctx.raw / total) * 100).toFixed(1);
                    return ` ${ctx.label}: ${pct}% (${fmtN(ctx.raw)})`;
                }
            }}
        }}
    });

    serviciosChart = new Chart(document.getElementById("serviciosChart"), {
        type: "pie",
        data: { labels: [], datasets: [{
            data: [],
            backgroundColor: serviciosPalette,
            borderColor: "#ffffff", borderWidth: 2
        }]},
        options: { plugins: {
            legend: { labels: { color: "#0b3c5d" } },
            tooltip: { callbacks: {
                label: ctx => {
                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                    const pct   = ((ctx.raw / total) * 100).toFixed(1);
                    return ` ${ctx.label}: ${pct}% (${fmtN(ctx.raw)} usos)`;
                }
            }}
        }}
    });

    ventasPorDiaChart = new Chart(document.getElementById("ventasPorDiaChart"), {
        type: "bar",
        data: {
            labels: ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"],
            datasets: [{
                label: "Ventas", data: [0,0,0,0,0,0],
                backgroundColor: "#6366f1", borderColor: "#4338ca",
                borderWidth: 1, borderRadius: 8
            }]
        },
        options: optsBarBase()
    });
}

async function cargarDashboard() {
    const inicio  = document.getElementById("fecha_inicio").value;
    const fin     = document.getElementById("fecha_fin").value;
    const negocio = document.getElementById("negocio_select").value;

    if (!inicio || !fin) return;

    const dias = (new Date(fin) - new Date(inicio)) / 86400000;
    if (dias > 186) {
        mostrarError("El rango máximo permitido es 6 meses (~186 días). Ajusta las fechas.");
        return;
    }
    ocultarError();

    try {
        const url = `/api/estadisticas/dashboard?inicio=${inicio}&fin=${fin}&id_negocio=${negocio}`;
        const res = await fetch(url);

        if (!res.ok) {
            const json = await res.json().catch(() => ({}));
            mostrarError(json.error || `Error ${res.status} al cargar datos.`);
            return;
        }

        const data = await res.json();

        const k = data.kpis || {};
        setKpi("ventasMes",     k.ingresos,         k.ingresos_pct);
        setKpi("gastosMes",     k.gastos,            k.gastos_pct);
        setKpi("gananciaMes",   k.ganancia,          k.ganancia_pct);
        setKpi("ticketPromedio",k.ticket_promedio,   k.ticket_pct);
        setKpi("saldoCobrar",   k.saldo_por_cobrar,  k.saldo_pct);

        const elTotal = document.getElementById("totalVentas");
        if (elTotal) elTotal.innerHTML = fmtN(k.total_ventas) + badgePct(k.ventas_pct);

        const elVentas = document.getElementById("ticketVentas");
        if (elVentas) elVentas.textContent = `${fmtN(k.num_ventas)} ventas`;

        if (data.ventas_semanales) {
            ventasSemanaChart.data.labels   = data.ventas_semanales.map(x => x.label);
            ventasSemanaChart.data.datasets[0].data = data.ventas_semanales.map(x => x.total);
            ventasSemanaChart.update();
        }
        if (data.gastos_semanales) {
            gastosChart.data.labels   = data.gastos_semanales.labels || [];
            gastosChart.data.datasets = aplicarColoresRojos(data.gastos_semanales.datasets || []);
            gastosChart.update();
        }
        if (data.ingresos_semanales) {
            ingresosChart.data.labels   = data.ingresos_semanales.map(x => x.label);
            ingresosChart.data.datasets[0].data = data.ingresos_semanales.map(x => x.total);
            ingresosChart.update();
        }
        if (data.unidades_semanales) {
            unidadesSemanaChart.data.labels   = data.unidades_semanales.map(x => x.label);
            unidadesSemanaChart.data.datasets[0].data = data.unidades_semanales.map(x => x.total);
            unidadesSemanaChart.update();
        }

        if (data.ventas_prepago) {
            tipoPagoChart.data.labels   = data.ventas_prepago.map(x => x.tipo);
            tipoPagoChart.data.datasets[0].data = data.ventas_prepago.map(x => x.total);
            tipoPagoChart.update();
        }
        if (data.uso_servicios) {
            serviciosChart.data.labels   = data.uso_servicios.map(x => x.nombre);
            serviciosChart.data.datasets[0].data = data.uso_servicios.map(x => x.total);
            serviciosChart.update();
        }
        if (data.ventas_por_dia) {
            ventasPorDiaChart.data.datasets[0].data = data.ventas_por_dia;
            ventasPorDiaChart.update();
        }

    } catch (err) {
        mostrarError("Error inesperado al cargar el dashboard.");
    }
}

function setKpi(id, valor, pct) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = fmt$(valor) + badgePct(pct);
}

function mostrarError(msg) {
    let el = document.getElementById("dashboard-error");
    if (!el) {
        el = document.createElement("div");
        el.id = "dashboard-error";
        el.style.cssText =
            "background:#fee2e2;color:#b91c1c;padding:10px 16px;" +
            "border-radius:8px;margin:12px 0;font-size:13px;font-weight:500;";
        document.querySelector(".date-selector").after(el);
    }
    el.textContent = "⚠️ " + msg;
    el.style.display = "block";
}

function ocultarError() {
    const el = document.getElementById("dashboard-error");
    if (el) el.style.display = "none";
}

function verVentasRelacionadas() {
    const inicio  = document.getElementById("fecha_inicio").value;
    const fin     = document.getElementById("fecha_fin").value;
    const negocio = document.getElementById("negocio_select").value;

    if (!inicio || !fin) {
        mostrarError("Selecciona un rango de fechas antes de ver las ventas.");
        return;
    }

    const params = new URLSearchParams({ fecha_inicio: inicio, fecha_fin: fin });
    if (negocio && negocio !== "all") params.set("id_negocio", negocio);

    window.open(`/ventas/historial?${params.toString()}`, "_blank");
}

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    cargarDashboard();
});