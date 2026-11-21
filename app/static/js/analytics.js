document.addEventListener("DOMContentLoaded", function () {
    const mapContainer = document.getElementById("map");
    if (!mapContainer) return;

    const linkFilter = document.getElementById("mapLinkFilter");
    const resetViewBtn = document.getElementById("resetMapViewBtn");
    const markerCountBadge = document.getElementById("markerCountBadge");
    const countryTableBody = document.getElementById("countryTableBody");

    // Initialize Leaflet Map centered at global view (zoom level 2)
    const map = L.map("map", {
        center: [20.0, 0.0],
        zoom: 2,
        minZoom: 2,
        maxZoom: 18,
    });

    // Add OpenStreetMap tile layer
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);

    let markersLayer = L.layerGroup().addTo(map);

    // Custom emerald icon
    const emeraldIcon = L.divIcon({
        className: "custom-emerald-pin-wrapper",
        html: `<div style="width: 14px; height: 14px; background-color: #10b981; border: 2.5px solid #ffffff; border-radius: 50%; box-shadow: 0 2px 6px rgba(0,0,0,0.35);"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
        popupAnchor: [0, -8]
    });

    function loadMapPoints(linkId = "") {
        const url = linkId ? `/api/analytics/map?link_id=${linkId}` : "/api/analytics/map";

        fetch(url)
            .then(res => res.json())
            .then(data => {
                markersLayer.clearLayers();
                const points = data.points || [];
                markerCountBadge.textContent = `${points.length} plotted location${points.length === 1 ? '' : 's'}`;

                if (points.length === 0) {
                    map.setView([20.0, 0.0], 2);
                    return;
                }

                const latLngs = [];

                points.forEach(pt => {
                    if (pt.lat !== null && pt.lon !== null) {
                        const marker = L.marker([pt.lat, pt.lon], { icon: emeraldIcon });
                        
                        const popupContent = `
                            <div style="font-family: inherit; font-size: 0.85rem; min-width: 190px;">
                                <div style="font-weight: 700; color: #0f172a; margin-bottom: 3px; font-size: 0.95rem;">
                                    <i class="bi bi-geo-alt-fill text-success" style="margin-right: 4px;"></i>${escapeHtml(pt.city)}, ${escapeHtml(pt.country)}
                                </div>
                                <div style="color: #64748b; font-size: 0.75rem; margin-bottom: 6px;">
                                    Approx: ${pt.lat.toFixed(4)}, ${pt.lon.toFixed(4)}
                                </div>
                                <div style="border-top: 1px solid #e2e8f0; padding-top: 6px; display: flex; flex-direction: column; gap: 3px;">
                                    <div><strong style="color: #334155;">Link:</strong> ${escapeHtml(pt.link_name)}</div>
                                    <div><strong style="color: #334155;">ISP:</strong> ${escapeHtml(pt.isp)}</div>
                                    <div><strong style="color: #334155;">Date:</strong> <span style="color: #64748b;">${escapeHtml(pt.timestamp)}</span></div>
                                </div>
                                <div style="margin-top: 6px; font-size: 0.68rem; color: #94a3b8; font-style: italic;">
                                    *Approximate IP location – not GPS
                                </div>
                            </div>
                        `;

                        marker.bindPopup(popupContent);
                        markersLayer.addLayer(marker);
                        latLngs.push([pt.lat, pt.lon]);
                    }
                });

                if (latLngs.length > 0) {
                    const bounds = L.latLngBounds(latLngs);
                    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 10 });
                }
            })
            .catch(err => console.error("Error loading map points:", err));
    }

    function loadCountryTable() {
        fetch("/api/analytics/countries?limit=15")
            .then(res => res.json())
            .then(data => {
                const countries = data.countries || [];
                if (countries.length === 0) {
                    countryTableBody.innerHTML = `
                        <tr>
                            <td colspan="4" class="text-center py-4 text-muted">
                                No regional visitor data recorded yet.
                            </td>
                        </tr>
                    `;
                    return;
                }

                countryTableBody.innerHTML = countries.map(c => `
                    <tr>
                        <td class="fw-semibold text-dark">${escapeHtml(c.country)}</td>
                        <td><span class="badge bg-light text-secondary border">${escapeHtml(c.country_code)}</span></td>
                        <td><span class="fw-bold">${c.count.toLocaleString()}</span></td>
                        <td>
                            <div class="d-flex align-items-center gap-2">
                                <div class="progress flex-grow-1" style="height: 6px;">
                                    <div class="progress-bar bg-success" role="progressbar" style="width: ${c.percentage}%" aria-valuenow="${c.percentage}" aria-valuemin="0" aria-valuemax="100"></div>
                                </div>
                                <span class="small text-muted" style="min-width: 42px;">${c.percentage}%</span>
                            </div>
                        </td>
                    </tr>
                `).join("");
            })
            .catch(err => {
                console.error("Error loading countries table:", err);
            });
    }

    // Filter change
    linkFilter.addEventListener("change", function () {
        loadMapPoints(this.value);
    });

    // Reset Map View
    resetViewBtn.addEventListener("click", function () {
        map.setView([20.0, 0.0], 2);
    });

    function escapeHtml(text) {
        if (!text) return "Not available";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Initial fetch
    loadMapPoints();
    loadCountryTable();
});
