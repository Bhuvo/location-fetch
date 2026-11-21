document.addEventListener("DOMContentLoaded", function () {
    const linksTableBody = document.getElementById("linksTableBody");
    const linksEmptyState = document.getElementById("linksEmptyState");
    const createLinkForm = document.getElementById("createLinkForm");
    const linkNameInput = document.getElementById("linkName");
    const saveLinkBtn = document.getElementById("saveLinkBtn");

    let deleteTargetId = null;
    const deleteModalEl = document.getElementById("deleteLinkModal");
    const deleteModal = deleteModalEl ? new bootstrap.Modal(deleteModalEl) : null;
    const deleteLinkNameEl = document.getElementById("deleteLinkName");
    const confirmDeleteBtn = document.getElementById("confirmDeleteLinkBtn");

    const createModalEl = document.getElementById("createLinkModal");
    const createModal = createModalEl ? new bootstrap.Modal(createModalEl) : null;

    // Load and render links
    function loadLinks() {
        fetch("/api/links")
            .then(res => res.json())
            .then(data => {
                const links = data.links || [];
                if (links.length === 0) {
                    linksTableBody.innerHTML = "";
                    linksEmptyState.classList.remove("d-none");
                    return;
                }

                linksEmptyState.classList.add("d-none");
                linksTableBody.innerHTML = links.map(link => {
                    const createdStr = link.created_at ? link.created_at.replace("T", " ").substring(0, 16) : "-";
                    return `
                        <tr id="link-row-${link.id}">
                            <td>
                                <div class="fw-bold text-dark">${escapeHtml(link.name)}</div>
                                <div class="text-muted" style="font-size: 0.75rem;">Token: <code>${link.token}</code></div>
                            </td>
                            <td>
                                <div class="input-group input-group-sm" style="max-width: 340px;">
                                    <input type="text" class="form-control bg-light font-monospace" value="${escapeHtml(link.tracking_url)}" readonly id="url-input-${link.id}">
                                    <button class="btn btn-outline-secondary copy-btn" data-url="${escapeHtml(link.tracking_url)}" title="Copy Link">
                                        <i class="bi bi-clipboard"></i>
                                    </button>
                                </div>
                            </td>
                            <td>
                                <div class="form-check form-switch">
                                    <input class="form-check-input status-toggle" type="checkbox" role="switch" data-id="${link.id}" ${link.is_active ? "checked" : ""}>
                                    <label class="form-check-label small ${link.is_active ? "text-success fw-semibold" : "text-muted"}">
                                        ${link.is_active ? "Active" : "Inactive"}
                                    </label>
                                </div>
                            </td>
                            <td>
                                <span class="badge ${link.consented_count > 0 ? "bg-emerald-light text-emerald" : "bg-light text-muted border"} px-2 py-1">
                                    <i class="bi bi-shield-check me-1"></i>${link.consented_count} visits
                                </span>
                            </td>
                            <td><span class="text-muted small">${createdStr}</span></td>
                            <td class="text-end">
                                <a href="${link.tracking_url}" target="_blank" class="btn btn-sm btn-light border me-1" title="Test Public Page">
                                    <i class="bi bi-box-arrow-up-right"></i>
                                </a>
                                <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${link.id}" data-name="${escapeHtml(link.name)}" title="Delete Link">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                }).join("");

                attachEventListeners();
            })
            .catch(err => {
                console.error("Error loading links:", err);
                linksTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">Error loading tracking links.</td></tr>`;
            });
    }

    function attachEventListeners() {
        // Copy to clipboard buttons
        document.querySelectorAll(".copy-btn").forEach(btn => {
            btn.addEventListener("click", function () {
                const url = this.getAttribute("data-url");
                navigator.clipboard.writeText(url).then(() => {
                    const originalHtml = this.innerHTML;
                    this.innerHTML = '<i class="bi bi-check text-success"></i>';
                    window.showToast("Tracking URL copied to clipboard!", "bg-success");
                    setTimeout(() => { this.innerHTML = originalHtml; }, 2000);
                }).catch(() => {
                    window.showToast("Failed to copy link. Please select manually.", "bg-danger");
                });
            });
        });

        // Status toggle switches
        document.querySelectorAll(".status-toggle").forEach(toggle => {
            toggle.addEventListener("change", function () {
                const linkId = this.getAttribute("data-id");
                const isActive = this.checked;
                const label = this.nextElementSibling;

                fetch(`/api/links/${linkId}`, {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": window.getCSRFToken()
                    },
                    body: JSON.stringify({ is_active: isActive })
                })
                .then(r => r.json())
                .then(res => {
                    if (res.success) {
                        label.textContent = isActive ? "Active" : "Inactive";
                        label.className = `form-check-label small ${isActive ? "text-success fw-semibold" : "text-muted"}`;
                        window.showToast(`Link is now ${isActive ? "active" : "deactivated"}.`, "bg-dark");
                    } else {
                        throw new Error(res.error || "Update failed");
                    }
                })
                .catch(err => {
                    this.checked = !isActive;
                    window.showToast("Failed to update status: " + err.message, "bg-danger");
                });
            });
        });

        // Delete buttons
        document.querySelectorAll(".delete-btn").forEach(btn => {
            btn.addEventListener("click", function () {
                deleteTargetId = this.getAttribute("data-id");
                const name = this.getAttribute("data-name");
                deleteLinkNameEl.textContent = `"${name}"`;
                deleteModal.show();
            });
        });
    }

    // Confirm Delete Link
    confirmDeleteBtn.addEventListener("click", function () {
        if (!deleteTargetId) return;
        confirmDeleteBtn.disabled = true;

        fetch(`/api/links/${deleteTargetId}`, {
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
                loadLinks();
            } else {
                window.showToast(res.error || "Failed to delete link.", "bg-danger");
            }
        })
        .catch(err => {
            confirmDeleteBtn.disabled = false;
            window.showToast("Network error deleting link.", "bg-danger");
        });
    });

    // Create Link Form Submit
    createLinkForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const name = linkNameInput.value.trim();
        if (!name) return;

        saveLinkBtn.disabled = true;
        saveLinkBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Creating...';

        fetch("/api/links", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": window.getCSRFToken()
            },
            body: JSON.stringify({ name: name })
        })
        .then(r => r.json())
        .then(res => {
            saveLinkBtn.disabled = false;
            saveLinkBtn.innerHTML = "Create Tracking Link";

            if (res.success) {
                linkNameInput.value = "";
                createModal.hide();
                window.showToast("Tracking link created successfully!", "bg-success");
                loadLinks();
            } else {
                window.showToast(res.error || "Failed to create tracking link.", "bg-danger");
            }
        })
        .catch(err => {
            saveLinkBtn.disabled = false;
            saveLinkBtn.innerHTML = "Create Tracking Link";
            window.showToast("Network error creating tracking link.", "bg-danger");
        });
    });

    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    loadLinks();
});
