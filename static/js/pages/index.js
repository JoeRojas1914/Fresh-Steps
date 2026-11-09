import { countUp } from '../base/helpers.js';

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

// ── Gráfica de la semana ──────────────────────────────────────────────────────
var _chart    = null;
var _rawChart = JSON.parse(document.getElementById("indexChartData").textContent);
var _canvas   = document.getElementById("miniVentasChart");
var _hoyIdx   = typeof _rawChart.hoyIdx === "number" ? _rawChart.hoyIdx : 6;

var AZUL       = "#1e7fd6";
var AZUL_CLARO = "#9cc8f0";

function _plural(n, uno, varios) { return n + " " + (n === 1 ? uno : varios); }

function _hastaHoy(valores) {
    return (valores || []).map(function(v, i) { return i > _hoyIdx ? null : v; });
}

function _suma(valores) {
    return (valores || []).reduce(function(a, v) { return a + (v || 0); }, 0);
}

function _actualizarVacio(ventas, unidades) {
    var vacio = document.getElementById("chartVacio");
    if (vacio) vacio.hidden = (_suma(ventas) + _suma(unidades)) > 0;
}

if (_canvas && _rawChart && window.Chart) {
    var tooltipStyle = {
        backgroundColor: "#ffffff",
        titleColor: "#0f172a",
        bodyColor: "#475569",
        borderColor: "#e2e8f0",
        borderWidth: 1,
        cornerRadius: 8,
        padding: 10,
        boxPadding: 4,
        titleFont: { weight: "600", size: 13 },
        bodyFont: { size: 12 }
    };

    var barra = function(color) {
        return {
            backgroundColor: color,
            borderWidth: 0,
            borderRadius: 4,
            borderSkipped: false,
            maxBarThickness: 22,
            categoryPercentage: 0.7,
            barPercentage: 0.9
        };
    };

    var ventas   = _hastaHoy(_rawChart.data);
    var unidades = _hastaHoy(_rawChart.unidades);

    _chart = new Chart(_canvas.getContext("2d"), {
        type: "bar",
        data: {
            labels: _rawChart.labels,
            datasets: [
                Object.assign({ label: "Ventas", data: ventas }, barra(AZUL)),
                Object.assign({ label: "Unidades recibidas", data: unidades }, barra(AZUL_CLARO))
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { display: false },
                tooltip: Object.assign({}, tooltipStyle, {
                    filter: function(c) { return c.raw !== null; },
                    callbacks: {
                        label: function(c) {
                            return c.datasetIndex === 1
                                ? " " + _plural(c.raw, "unidad recibida", "unidades recibidas")
                                : " " + _plural(c.raw, "venta", "ventas");
                        }
                    }
                })
            },
            scales: {
                y: {
                    beginAtZero: true,
                    suggestedMax: 4,
                    ticks: { precision: 0, maxTicksLimit: 4, color: "#94a3b8", font: { size: 11 } },
                    grid: { color: "rgba(226,232,240,0.7)" },
                    border: { display: false }
                },
                x: {
                    grid: { display: false },
                    border: { display: false },
                    ticks: {
                        callback: function(value, i) {
                            var lbl = this.getLabelForValue(value);
                            return this.chart.width < 480 ? String(lbl).split(" ")[0] : lbl;
                        },
                        color: function(c) { return c.index === _hoyIdx ? "#0b3c5d" : "#64748b"; },
                        font:  function(c) { return { size: 11, weight: c.index === _hoyIdx ? "700" : "400" }; }
                    }
                }
            }
        }
    });

    _actualizarVacio(ventas, unidades);
}

// ── Mostrar/ocultar montos sensibles ────────────────────────────────────────
(function() {
    var toggleBtn = document.getElementById("toggleMontos");
    if (!toggleBtn) return;

    var STORAGE_KEY = "fs_montos_sesion";
    var sesion      = toggleBtn.dataset.sesion || "";

    var texto = toggleBtn.querySelector(".home-toggle-texto");

    function aplicar(visible) {
        document.body.classList.toggle("montos-visibles", visible);
        toggleBtn.setAttribute("aria-pressed", visible ? "true" : "false");
        if (texto) texto.textContent = visible ? "Ocultar montos" : "Mostrar montos";
    }

    var guardado = null;
    try {
        localStorage.removeItem("fs_montos_visibles");   // formato anterior, sin sesión
        guardado = localStorage.getItem(STORAGE_KEY);
    } catch (e) { /* almacenamiento bloqueado: siempre censurado */ }
    aplicar(sesion !== "" && guardado === sesion);

    toggleBtn.addEventListener("click", function() {
        var visible = toggleBtn.getAttribute("aria-pressed") !== "true";
        aplicar(visible);
        try {
            if (visible && sesion) localStorage.setItem(STORAGE_KEY, sesion);
            else localStorage.removeItem(STORAGE_KEY);
        } catch (e) { /* sin almacenamiento: solo dura esta página */ }
    });
}());

// ── Negocio pills — AJAX ──────────────────────────────────────────────────────
var _isAdmin = document.querySelector("[data-kpi='ingresos_mes']") !== null;

function _setKpi(key, value, monetary) {
    var el = document.querySelector("[data-kpi='" + key + "']");
    if (!el) return;
    countUp(el, value, monetary, 500);
}
var _loadingTimer = null;

function _setLoading(on) {
    clearTimeout(_loadingTimer);
    var aplicar = function(estado) {
        document.querySelectorAll("[data-kpi]").forEach(function(el) {
            el.classList.toggle("is-skeleton", estado);
        });
        var chart = document.querySelector(".hoy-chart");
        if (chart) chart.classList.toggle("is-cargando", estado);
    };
    if (on) _loadingTimer = setTimeout(function() { aplicar(true); }, 150);
    else aplicar(false);
}

document.addEventListener("click", function(e) {
    var pill = e.target.closest(".negocio-pill[data-negocio]");
    if (!pill) return;
    e.preventDefault();

    var negocio = pill.dataset.negocio;

    document.querySelectorAll(".negocio-pill").forEach(function(p) {
        p.classList.toggle("active", p.dataset.negocio === negocio);
    });

    document.querySelectorAll("a.kpi-hoy-card--link, a.entregar-card").forEach(function(a) {
        var url = new URL(a.href, window.location.href);
        if (negocio === "all") url.searchParams.delete("id_negocio");
        else url.searchParams.set("id_negocio", negocio);
        a.href = url.pathname + url.search;
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
        _setKpi("ventas_entregadas_hoy", data.ventas_entregadas_hoy, false);
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
            if (typeof data.chart_hoy_idx === "number") _hoyIdx = data.chart_hoy_idx;
            var v = _hastaHoy(data.chart_data);
            var u = _hastaHoy(data.chart_unidades);
            _chart.data.labels            = data.chart_labels;
            _chart.data.datasets[0].data  = v;
            _chart.data.datasets[1].data  = u;
            _chart.update("none");
            _actualizarVacio(v, u);
        }
    })
    .catch(function() { _setLoading(false); });
});
