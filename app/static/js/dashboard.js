document.addEventListener("DOMContentLoaded", function () {
    // Color palette matching dark navy & emerald design system
    const emeraldPrimary = "#10b981";
    const emeraldHover = "#059669";
    const slateDark = "#0f172a";
    const chartColors = [
        "#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ec4899", 
        "#06b6d4", "#64748b", "#84cc16", "#f97316", "#6366f1"
    ];

    let timelineChartInstance = null;
    let countryChartInstance = null;
    let browserChartInstance = null;
    let osChartInstance = null;

    // 1. Load Overview KPIs
    function loadKPIs() {
        fetch("/api/analytics/overview")
            .then(res => res.json())
            .then(data => {
                document.getElementById("kpiTotalLinks").textContent = data.total_tracking_links.toLocaleString();
                document.getElementById("kpiTotalConsents").textContent = data.total_consent_events.toLocaleString();
                document.getElementById("kpiUniqueIps").textContent = data.unique_ip_addresses.toLocaleString();
                document.getElementById("kpiCountries").textContent = data.countries_detected.toLocaleString();
                document.getElementById("kpiCities").textContent = data.cities_detected.toLocaleString();
            })
            .catch(err => console.error("Error loading KPIs:", err));
    }

    // 2. Load Timeline Chart
    function loadTimelineChart() {
        fetch("/api/analytics/timeline?days=14")
            .then(res => res.json())
            .then(res => {
                const ctx = document.getElementById("timelineChart").getContext("2d");
                if (timelineChartInstance) timelineChartInstance.destroy();

                timelineChartInstance = new Chart(ctx, {
                    type: "line",
                    data: {
                        labels: res.labels,
                        datasets: [{
                            label: "Consented Visits",
                            data: res.data,
                            borderColor: emeraldPrimary,
                            backgroundColor: "rgba(16, 185, 129, 0.12)",
                            borderWidth: 2.5,
                            fill: true,
                            tension: 0.35,
                            pointBackgroundColor: emeraldPrimary,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                backgroundColor: slateDark,
                                padding: 10,
                                cornerRadius: 8,
                            }
                        },
                        scales: {
                            x: {
                                grid: { display: false },
                                ticks: { font: { size: 11 }, color: "#64748b" }
                            },
                            y: {
                                beginAtZero: true,
                                ticks: { precision: 0, font: { size: 11 }, color: "#64748b" },
                                grid: { color: "rgba(226, 232, 240, 0.8)" }
                            }
                        }
                    }
                });
            })
            .catch(err => console.error("Error loading timeline:", err));
    }

    // 3. Load Country Distribution Chart
    function loadCountryChart() {
        fetch("/api/analytics/countries?limit=6")
            .then(res => res.json())
            .then(res => {
                const ctx = document.getElementById("countryChart").getContext("2d");
                if (countryChartInstance) countryChartInstance.destroy();

                const countries = res.countries || [];
                const labels = countries.length > 0 ? countries.map(c => c.country) : ["No data yet"];
                const data = countries.length > 0 ? countries.map(c => c.count) : [0];

                countryChartInstance = new Chart(ctx, {
                    type: "doughnut",
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: countries.length > 0 ? chartColors.slice(0, countries.length) : ["#e2e8f0"],
                            borderWidth: 2,
                            borderColor: "#ffffff"
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: "68%",
                        plugins: {
                            legend: {
                                position: "bottom",
                                labels: { boxWidth: 12, font: { size: 11 }, color: "#475569" }
                            }
                        }
                    }
                });
            })
            .catch(err => console.error("Error loading country distribution:", err));
    }

    // 4. Load Browser Distribution Chart
    function loadBrowserChart() {
        fetch("/api/analytics/browsers")
            .then(res => res.json())
            .then(res => {
                const ctx = document.getElementById("browserChart").getContext("2d");
                if (browserChartInstance) browserChartInstance.destroy();

                const browsers = res.browsers || [];
                const labels = browsers.length > 0 ? browsers.map(b => b.browser) : ["No data"];
                const data = browsers.length > 0 ? browsers.map(b => b.count) : [0];

                browserChartInstance = new Chart(ctx, {
                    type: "doughnut",
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: browsers.length > 0 ? chartColors.slice(0, browsers.length) : ["#e2e8f0"],
                            borderWidth: 2,
                            borderColor: "#ffffff"
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: "65%",
                        plugins: {
                            legend: {
                                position: "bottom",
                                labels: { boxWidth: 12, font: { size: 11 }, color: "#475569" }
                            }
                        }
                    }
                });
            })
            .catch(err => console.error("Error loading browsers:", err));
    }

    // 5. Load OS Distribution Chart
    function loadOsChart() {
        fetch("/api/analytics/os")
            .then(res => res.json())
            .then(res => {
                const ctx = document.getElementById("osChart").getContext("2d");
                if (osChartInstance) osChartInstance.destroy();

                const osList = res.os || [];
                const labels = osList.length > 0 ? osList.map(o => o.os) : ["No data"];
                const data = osList.length > 0 ? osList.map(o => o.count) : [0];

                osChartInstance = new Chart(ctx, {
                    type: "doughnut",
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: osList.length > 0 ? chartColors.slice(0, osList.length) : ["#e2e8f0"],
                            borderWidth: 2,
                            borderColor: "#ffffff"
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: "65%",
                        plugins: {
                            legend: {
                                position: "bottom",
                                labels: { boxWidth: 12, font: { size: 11 }, color: "#475569" }
                            }
                        }
                    }
                });
            })
            .catch(err => console.error("Error loading OS distribution:", err));
    }

    // 6. Load Recent Consented Visits
    function loadRecentVisits() {
        const tableBody = document.getElementById("recentVisitsTable");
        fetch("/api/visitors?per_page=6")
            .then(res => res.json())
            .then(res => {
                const records = res.records || [];
                if (records.length === 0) {
                    tableBody.innerHTML = `
                        <tr>
                            <td colspan="6" class="text-center py-4 text-muted">
                                <i class="bi bi-inbox fs-4 d-block mb-1 text-secondary"></i>
                                No consented visitor records yet. Create a tracking link to begin collecting data.
                            </td>
                        </tr>
                    `;
                    return;
                }

                tableBody.innerHTML = records.map(r => {
                    const timeStr = r.consent_timestamp ? r.consent_timestamp.replace("T", " ").substring(0, 19) : "-";
                    const locParts = [r.city, r.country].filter(p => p && p !== "Not available");
                    const loc = locParts.length > 0 ? locParts.join(", ") : "Not available";
                    
                    return `
                        <tr>
                            <td><span class="text-muted small">${timeStr}</span></td>
                            <td><span class="fw-semibold text-dark">${r.tracking_link_name}</span></td>
                            <td><code class="text-secondary">${r.ip_address}</code></td>
                            <td><i class="bi bi-geo-alt text-emerald me-1"></i>${loc}</td>
                            <td><span class="text-truncate d-inline-block" style="max-width: 180px;">${r.isp || r.organization || 'Not available'}</span></td>
                            <td><span class="badge bg-light text-secondary border">${r.browser} / ${r.operating_system}</span></td>
                        </tr>
                    `;
                }).join("");
            })
            .catch(err => {
                console.error("Error loading recent visits:", err);
                tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-3">Error loading records.</td></tr>`;
            });
    }

    // Initialize all widgets
    loadKPIs();
    loadTimelineChart();
    loadCountryChart();
    loadBrowserChart();
    loadOsChart();
    loadRecentVisits();
});
