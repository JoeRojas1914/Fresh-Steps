function countUp(el, target, monetary, duration) {
    duration = duration || 900;
    const start = performance.now();
    const fmt = monetary
        ? function(v) { return "$" + v.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
        : function(v) { return Math.floor(v).toLocaleString("es-MX"); };
    function tick(now) {
        var ease = 1 - Math.pow(1 - Math.min((now - start) / duration, 1), 3);
        el.textContent = fmt(target * ease);
        if (ease < 1) requestAnimationFrame(tick);
        else el.textContent = fmt(target);
    }
    requestAnimationFrame(tick);
}

var _countObserver = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
        if (!entry.isIntersecting) return;
        _countObserver.unobserve(entry.target);
        var el       = entry.target;
        var target   = parseFloat(el.dataset.countTarget);
        var monetary = el.dataset.countMonetary === "1";
        if (!isNaN(target)) countUp(el, target, monetary);
    });
}, { threshold: 0.2 });

document.querySelectorAll(".kpi-hoy-num, .accion-num, .mes-num").forEach(function(el) {
    var raw      = el.textContent.trim();
    var monetary = raw.startsWith("$");
    var target   = parseFloat(raw.replace(/[$,]/g, ""));
    if (!isNaN(target) && target > 0) {
        el.dataset.countTarget   = target;
        el.dataset.countMonetary = monetary ? "1" : "0";
        _countObserver.observe(el);
    }
});

// ── Chart ─────────────────────────────────────────────────────────────────────
var _chart = null;
var _rawChart = JSON.parse(document.getElementById("indexChartData").textContent);
var _canvas   = document.getElementById("miniVentasChart");

if (_canvas && _rawChart) {
    var ctx      = _canvas.getContext("2d");
    var gradient = ctx.createLinearGradient(0, 0, 0, 110);
    gradient.addColorStop(0, "rgba(47,164,255,0.35)");
    gradient.addColorStop(1, "rgba(47,164,255,0)");

    _chart = new Chart(ctx, {
        type: "line",
        data: {
            labels: _rawChart.labels,
            datasets: [{
                data: _rawChart.data,
                borderColor: "#2fa4ff",
                borderWidth: 2,
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: "#2fa4ff",
                pointHoverBorderColor: "#ffffff",
                pointHoverBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: "index",
                    intersect: false,
                    callbacks: {
                        label: function(c) { return " " + c.raw + " venta" + (c.raw !== 1 ? "s" : ""); }
                    }
                }
            },
            scales: {
                y: { display: false, beginAtZero: true },
                x: { display: false }
            }
        }
    });
}

// ── Negocio pills — AJAX ──────────────────────────────────────────────────────
var _isAdmin = document.querySelector("[data-kpi='ingresos_mes']") !== null;

function _setKpi(key, value, monetary) {
    var el = document.querySelector("[data-kpi='" + key + "']");
    if (!el) return;
    countUp(el, value, monetary, 500);
}

function _setLoading(on) {
    document.querySelectorAll("[data-kpi]").forEach(function(el) {
        el.classList.toggle("kpi-loading", on);
    });
}

document.addEventListener("click", function(e) {
    var pill = e.target.closest(".negocio-pill[data-negocio]");
    if (!pill) return;
    e.preventDefault();

    var negocio = pill.dataset.negocio;

    document.querySelectorAll(".negocio-pill").forEach(function(p) {
        p.classList.toggle("active", p.dataset.negocio === negocio);
    });

    _setLoading(true);

    fetch("/api/index/kpis?negocio=" + encodeURIComponent(negocio), {
        headers: { "X-Requested-With": "XMLHttpRequest" }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        _setLoading(false);

        _setKpi("ventas_hoy",          data.ventas_hoy,              false);
        _setKpi("unidades_recibidas",  data.unidades_recibidas_hoy,  false);
        _setKpi("unidades_entregadas", data.unidades_entregadas_hoy, false);
        _setKpi("total_pendientes",    data.total_pendientes,        false);
        _setKpi("total_entregas",      data.total_entregas,          false);

        if (_isAdmin) {
            if (data.ingresos_hoy !== null) {
                _setKpi("ingresos_hoy", data.ingresos_hoy, true);
            }
            if (data.kpis_mes) {
                _setKpi("ingresos_mes", data.kpis_mes.ingresos, true);
                _setKpi("gastos_mes",   data.kpis_mes.gastos,   true);
                _setKpi("ganancia_mes", data.kpis_mes.ganancia, true);
            }
        }

        if (_chart && data.chart_labels && data.chart_data) {
            _chart.data.labels            = data.chart_labels;
            _chart.data.datasets[0].data  = data.chart_data;
            _chart.update("none");
        }
    })
    .catch(function() { _setLoading(false); });
});
