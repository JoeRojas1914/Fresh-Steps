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
