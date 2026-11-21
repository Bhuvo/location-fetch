document.addEventListener("DOMContentLoaded", function () {
    const token = window.TRACKING_TOKEN;
    if (!token) return;

    const consentContainer = document.getElementById("consentContainer");
    const loadingState = document.getElementById("loadingState");
    const consentedState = document.getElementById("consentedState");
    const declinedState = document.getElementById("declinedState");

    const btnAllow = document.getElementById("btnAllow");
    const btnDecline = document.getElementById("btnDecline");
    const displayLocation = document.getElementById("displayLocation");
    const consentSuccessMsg = document.getElementById("consentSuccessMsg");

    function showState(elementToShow) {
        consentContainer.classList.add("d-none");
        loadingState.classList.add("d-none");
        consentedState.classList.add("d-none");
        declinedState.classList.add("d-none");

        elementToShow.classList.remove("d-none");
    }

    // Allow & Continue Consent Flow
    btnAllow.addEventListener("click", function () {
        showState(loadingState);

        fetch(`/api/track/${encodeURIComponent(token)}/consent`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.error || "Request failed"); });
            }
            return response.json();
        })
        .then(data => {
            showState(consentedState);
            if (data.approximate_location) {
                const loc = data.approximate_location;
                const parts = [loc.city, loc.country].filter(p => p && p !== "Not available");
                displayLocation.textContent = parts.length > 0 ? parts.join(", ") : "Recorded (IP Geolocation)";
            }
            if (data.status === "already_recorded") {
                consentSuccessMsg.textContent = "Your consent was already recently recorded. Thank you!";
            }
        })
        .catch(err => {
            console.error("Consent submission error:", err);
            showState(consentContainer);
            alert("An error occurred while submitting your consent: " + err.message);
        });
    });

    // Decline Flow
    btnDecline.addEventListener("click", function () {
        showState(loadingState);

        fetch(`/api/track/${encodeURIComponent(token)}/decline`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        })
        .then(response => response.json())
        .then(data => {
            showState(declinedState);
        })
        .catch(err => {
            console.error("Decline submission error:", err);
            // Even if network fails on decline, prioritize user privacy
            showState(declinedState);
        });
    });
});
