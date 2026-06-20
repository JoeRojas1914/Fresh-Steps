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
        var el      = entry.target;
        var target  = parseFloat(el.dataset.countTarget);
        var monetary = el.dataset.countMonetary === "1";
        if (!isNaN(target)) countUp(el, target, monetary);
    });
}, { threshold: 0.2 });

document.querySelectorAll(".kpi-hoy-num, .accion-num, .mes-num").forEach(function(el) {
    var raw = el.textContent.trim();
    var monetary = raw.startsWith("$");
    var target = parseFloat(raw.replace(/[$,]/g, ""));
    if (!isNaN(target) && target > 0) {
        el.dataset.countTarget  = target;
        el.dataset.countMonetary = monetary ? "1" : "0";
        _countObserver.observe(el);
    }
});

const raw    = JSON.parse(document.getElementById("indexChartData").textContent);
const canvas = document.getElementById("miniVentasChart");

if (canvas && raw) {
    const ctx      = canvas.getContext("2d");
    const gradient = ctx.createLinearGradient(0, 0, 0, 110);
    gradient.addColorStop(0, "rgba(47,164,255,0.35)");
    gradient.addColorStop(1, "rgba(47,164,255,0)");

    new Chart(ctx, {
        type: "line",
        data: {
            labels: raw.labels,
            datasets: [{
                data: raw.data,
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
                        label: c => ` ${c.raw} venta${c.raw !== 1 ? "s" : ""}`
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
