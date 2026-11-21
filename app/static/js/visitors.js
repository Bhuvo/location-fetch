document.addEventListener("DOMContentLoaded", function () {
    const tableBody = document.getElementById("visitorsTableBody");
    const emptyState = document.getElementById("visitorsEmptyState");
    const paginationContainer = document.getElementById("paginationContainer");
    const paginationSummary = document.getElementById("paginationSummary");
    const paginationNav = document.getElementById("paginationNav");

    const filterCity = document.getElementById("filterCity");
    const filterCountry = document.getElementById("filterCountry");
    const filterLink = document.getElementById("filterLink");
    const filterStartDate = document.getElementById("filterStartDate");
    const filterEndDate = document.getElementById("filterEndDate");
    const applyFiltersBtn = document.getElementById("applyFiltersBtn");
    const resetFiltersBtn = document.getElementById("resetFiltersBtn");
    const exportCsvBtn = document.getElementById("exportCsvBtn");

    let currentPage = 1;
    let deleteTargetId = null;

    // Modals
    const detailModalEl = document.getElementById("recordDetailModal");
    const detailModal = detailModalEl ? new bootstrap.Modal(detailModalEl) : null;

    const deleteModalEl = document.getElementById("deleteRecordModal");
    const deleteModal = deleteModalEl ? new bootstrap.Modal(deleteModalEl) : null;
    const confirmDeleteBtn = document.getElementById("confirmDeleteRecordBtn");

    function fetchRecords(page = 1) {
        currentPage = page;
        const params = new URLSearchParams({
            page: page,
            per_page: 15,
            city: filterCity.value.trim(),
            country: filterCountry.value.trim(),
            link_id: filterLink.value,
            start_date: filterStartDate.value,
            end_date: filterEndDate.value
        });

        tableBody.innerHTML = `<tr><td colspan="11" class="text-center py-4 text-muted"><div class="spinner-border spinner-border-sm text-secondary me-2"></div>Loading records...</td></tr>`;

        fetch(`/api/visitors?${params.toString()}`)
            .then(res => res.json())
            .then(data => {
                const records = data.records || [];
                if (records.length === 0) {
                    tableBody.innerHTML = "";
                    emptyState.classList.remove("d-none");
                    paginationContainer.classList.add("d-none");
                    return;
                }

                emptyState.classList.add("d-none");
                paginationContainer.classList.remove("d-none");

                tableBody.innerHTML = records.map(r => {
                    const timeStr = r.consent_timestamp ? r.consent_timestamp.replace("T", " ").substring(0, 19) : "-";
                    const conf = r.confidence || "UNKNOWN";
                    let confBadgeClass = "bg-light text-secondary border";
                    if (conf === "HIGH") confBadgeClass = "bg-success-subtle text-success border border-success-subtle";
                    else if (conf === "MEDIUM") confBadgeClass = "bg-warning-subtle text-warning border border-warning-subtle";
                    else if (conf === "LOW") confBadgeClass = "bg-danger-subtle text-danger border border-danger-subtle";

                    const centroidPill = r.is_city_centre 
                        ? `<span class="badge bg-danger text-white ms-1" title="City-center centroid detected (e.g. 13.0878, 80.2785)"><i class="bi bi-geo-fill"></i> Centroid</span>` 
                        : "";

                    return `
                        <tr>
                            <td><span class="small text-muted">${timeStr}</span></td>
                            <td><span class="fw-semibold text-dark">${escapeHtml(r.tracking_link_name)}</span></td>
                            <td><code class="text-secondary">${escapeHtml(r.ip_address)}</code></td>
                            <td><span class="fw-medium">${escapeHtml(r.country)}</span></td>
                            <td>${escapeHtml(r.city)}</td>
                            <td>
                                <span class="badge ${confBadgeClass}">${conf}</span>
                                ${centroidPill}
                            </td>
                            <td><span class="text-truncate d-inline-block" style="max-width: 140px;" title="${escapeHtml(r.isp)}">${escapeHtml(r.isp)}</span></td>
                            <td><span class="small">${escapeHtml(r.browser)}</span></td>
                            <td><span class="small">${escapeHtml(r.operating_system)}</span></td>
                            <td class="text-end">
                                <button class="btn btn-sm btn-light border view-btn me-1" data-id="${r.id}" title="View Details">
                                    <i class="bi bi-eye"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${r.id}" title="Delete Record">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                }).join("");

                // Render pagination summary & buttons
                const startIdx = (data.page - 1) * data.per_page + 1;
                const endIdx = Math.min(data.page * data.per_page, data.total);
                paginationSummary.textContent = `Showing ${startIdx} to ${endIdx} of ${data.total} records`;

                renderPaginationControls(data.page, data.pages);
                attachActionListeners();
            })
            .catch(err => {
                console.error("Error loading records:", err);
                tableBody.innerHTML = `<tr><td colspan="11" class="text-center text-danger py-4">Error loading visitor records.</td></tr>`;
            });
    }

    function renderPaginationControls(curr, totalPages) {
        if (totalPages <= 1) {
            paginationNav.innerHTML = "";
            return;
        }

        let navHtml = `
            <li class="page-item ${curr <= 1 ? "disabled" : ""}">
                <button class="page-link" data-page="${curr - 1}">&laquo;</button>
            </li>
        `;

        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= curr - 2 && i <= curr + 2)) {
                navHtml += `
                    <li class="page-item ${i === curr ? "active" : ""}">
                        <button class="page-link" data-page="${i}">${i}</button>
                    </li>
                `;
            } else if (i === curr - 3 || i === curr + 3) {
                navHtml += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }

        navHtml += `
            <li class="page-item ${curr >= totalPages ? "disabled" : ""}">
                <button class="page-link" data-page="${curr + 1}">&raquo;</button>
            </li>
        `;

        paginationNav.innerHTML = navHtml;

        paginationNav.querySelectorAll(".page-link").forEach(btn => {
            btn.addEventListener("click", function () {
                const targetPage = parseInt(this.getAttribute("data-page"), 10);
                if (targetPage && targetPage !== curr) {
                    fetchRecords(targetPage);
                }
            });
        });
    }

    function attachActionListeners() {
        // View Details
        document.querySelectorAll(".view-btn").forEach(btn => {
            btn.addEventListener("click", function () {
                const recordId = this.getAttribute("data-id");
                fetch(`/api/visitors/${recordId}`)
                    .then(res => res.json())
                    .then(record => {
                        document.getElementById("modalIp").textContent = record.ip_address;
                        document.getElementById("modalLink").textContent = `${record.tracking_link_name} (${record.tracking_link_token})`;
                        document.getElementById("modalCity").textContent = record.city;
                        document.getElementById("modalRegion").textContent = record.region;
                        document.getElementById("modalCountry").textContent = `${record.country} (${record.country_code})`;
                        document.getElementById("modalPostal").textContent = record.postal_code;
                        
                        const coords = (record.latitude !== null && record.longitude !== null) 
                            ? `${record.latitude.toFixed(4)}, ${record.longitude.toFixed(4)}`
                            : "Not available";
                        document.getElementById("modalCoords").textContent = coords;

                        document.getElementById("modalTimezone").textContent = record.timezone;
                        document.getElementById("modalIsp").textContent = record.isp;
                        document.getElementById("modalOrg").textContent = record.organization;
                        document.getElementById("modalAsn").textContent = record.asn;
                        document.getElementById("modalBrowser").textContent = record.browser;
                        document.getElementById("modalOs").textContent = record.operating_system;
                        document.getElementById("modalRadius").textContent = record.accuracy_radius ? `${record.accuracy_radius} km` : "Not specified";
                        document.getElementById("modalProvider").textContent = record.provider || "Not available";
                        
                        const confEl = document.getElementById("modalConfidence");
                        const conf = record.confidence || "UNKNOWN";
                        confEl.textContent = conf;
                        confEl.className = "badge";
                        if (conf === "HIGH") confEl.className = "badge bg-success";
                        else if (conf === "MEDIUM") confEl.className = "badge bg-warning text-dark";
                        else if (conf === "LOW") confEl.className = "badge bg-danger";
                        else confEl.className = "badge bg-secondary";

                        const centroidBadge = document.getElementById("modalCentroidBadge");
                        if (record.is_city_centre) {
                            centroidBadge.classList.remove("d-none");
                        } else {
                            centroidBadge.classList.add("d-none");
                        }

                        const diagLink = document.getElementById("modalDiagLink");
                        if (diagLink) {
                            diagLink.href = `/admin/diagnostics`;
                            diagLink.onclick = function() {
                                sessionStorage.setItem("diag_target_ip", record.ip_address);
                            };
                        }

                        document.getElementById("modalConsentTime").textContent = record.consent_timestamp 
                            ? `${record.consent_timestamp.replace("T", " ").substring(0, 19)} UTC`
                            : "Not recorded";

                        detailModal.show();
                    })
                    .catch(err => {
                        window.showToast("Failed to retrieve record details.", "bg-danger");
                    });
            });
        });

        // Delete
        document.querySelectorAll(".delete-btn").forEach(btn => {
            btn.addEventListener("click", function () {
                deleteTargetId = this.getAttribute("data-id");
                deleteModal.show();
            });
        });
    }

    // Confirm Delete
    confirmDeleteBtn.addEventListener("click", function () {
        if (!deleteTargetId) return;
        confirmDeleteBtn.disabled = true;

        fetch(`/api/visitors/${deleteTargetId}`, {
            method: "DELETE",
            headers: {
                "X-CSRFToken": window.getCSRFToken()
            }
        })
        .then(r => r.json())
        .then(res => {
            confirmDeleteBtn.disabled = false;
            deleteModal.hide();
            if (res.success) {
                window.showToast(res.message, "bg-success");
                fetchRecords(currentPage);
            } else {
                window.showToast(res.error || "Failed to delete record.", "bg-danger");
            }
        })
        .catch(err => {
            confirmDeleteBtn.disabled = false;
            window.showToast("Network error deleting record.", "bg-danger");
        });
    });

    // Apply & Reset Filters
    applyFiltersBtn.addEventListener("click", () => fetchRecords(1));

    resetFiltersBtn.addEventListener("click", function () {
        filterCity.value = "";
        filterCountry.value = "";
        filterLink.value = "";
        filterStartDate.value = "";
        filterEndDate.value = "";
        fetchRecords(1);
    });

    // Export CSV
    exportCsvBtn.addEventListener("click", function () {
        const params = new URLSearchParams({
            city: filterCity.value.trim(),
            country: filterCountry.value.trim(),
            link_id: filterLink.value,
            start_date: filterStartDate.value,
            end_date: filterEndDate.value
        });
        window.location.href = `/api/visitors/export?${params.toString()}`;
    });

    function escapeHtml(text) {
        if (text === null || text === undefined) return "Not available";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Initial load
    fetchRecords(1);
});
