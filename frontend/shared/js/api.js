/**
 * Shared API helper for BidBoard frontend.
 * Wraps fetch with JSON headers and response envelope unwrapping.
 */

async function apiFetch(url, options = {}) {
    const defaults = {
        headers: { "Content-Type": "application/json" },
    };
    const res = await fetch(url, { ...defaults, ...options });
    const json = await res.json();

    if (json.code >= 400) {
        throw new Error(json.message || "An error occurred.");
    }

    return json.data;
}

/**
 * Fetch user details from User Service.
 * Returns { userId, email, name, stripeId, createdAt }
 */
async function fetchUser(userId) {
    return apiFetch(`${CONFIG.USER_API}/users/${userId}`);
}

/**
 * Load current user details and update the navbar.
 * Call this on every page load. Pass the userId for the current role.
 */
async function loadNavbarUser(userId) {
    try {
        const user = await fetchUser(userId);
        const el = document.getElementById("navbar-user-name");
        if (el) el.textContent = user.name;
    } catch (e) {
        console.error("Failed to load user details:", e);
    }
}

/**
 * Get a query parameter from the current URL.
 */
function getQueryParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
}

/**
 * Return an outline badge class for a listing status.
 */
function statusBadgeClass(status) {
    switch (status) {
        case "SCHEDULED": return "badge-status-scheduled";
        case "ACTIVE": return "badge-status-active";
        case "CLOSED_PENDING_PAYMENT": return "badge-status-closed-pending";
        case "SOLD": return "badge-status-sold";
        case "FAILED_NO_ELIGIBLE_BIDDER": return "badge-status-failed";
        default: return "badge-status-default";
    }
}

/**
 * Return a seller-friendly display label for a listing status.
 */
function statusLabel(status) {
    switch (status) {
        case "SCHEDULED": return "Scheduled";
        case "ACTIVE": return "Live";
        case "CLOSED_PENDING_PAYMENT": return "Processing";
        case "SOLD": return "Sold";
        case "FAILED_NO_ELIGIBLE_BIDDER": return "Unsold";
        default: return status;
    }
}

/**
 * Return an outline badge class for an offer status.
 */
function offerBadgeClass(status) {
    switch (status) {
        case "PENDING": return "badge-offer-pending";
        case "COUNTERED": return "badge-offer-countered";
        case "ACCEPTED": return "badge-offer-accepted";
        case "REJECTED": return "badge-offer-rejected";
        case "CANCELLED": return "badge-offer-cancelled";
        default: return "badge-offer-default";
    }
}

/**
 * Return a display label for an offer status.
 */
function offerLabel(status) {
    switch (status) {
        case "PENDING": return "Pending";
        case "COUNTERED": return "Countered";
        case "ACCEPTED": return "Accepted";
        case "REJECTED": return "Rejected";
        case "CANCELLED": return "Cancelled";
        default: return status;
    }
}

/**
 * Format a number as currency (SGD).
 */
function formatPrice(amount) {
    return `$${Number(amount).toFixed(2)}`;
}

/**
 * Parse a UTC datetime string from the API.
 * API returns times without "Z" suffix — append it so JS treats them as UTC.
 */
function parseUtcDate(isoString) {
    if (!isoString) return null;
    const s = isoString.endsWith("Z") ? isoString : isoString + "Z";
    return new Date(s);
}

/**
 * Format a UTC datetime string from the API for display (in local/SGT time).
 */
function formatDateTime(isoString) {
    if (!isoString) return "—";
    const d = parseUtcDate(isoString);
    return d.toLocaleString("en-SG", {
        dateStyle: "medium",
        timeStyle: "short",
    });
}
