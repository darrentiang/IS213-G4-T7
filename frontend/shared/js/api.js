/**
 * Shared API helper for BidBoard frontend.
 * Wraps fetch with JSON headers and response envelope unwrapping.
 */

/** Re-render Lucide icons after dynamic HTML insertion. */
function refreshIcons() {
    if (typeof lucide !== "undefined") lucide.createIcons();
}

async function apiFetch(url, options = {}) {
    const buyerId = parseInt(localStorage.getItem("buyerId")) || 2;
    const defaults = {
        headers: {
            "Content-Type": "application/json",
            "X-Buyer-Id": String(buyerId),
        },
    };
    const res = await fetch(url, { ...defaults, ...options });
    const json = await res.json();

    // Handle Kong gateway errors (429 rate limit, 502 bad gateway, etc.)
    // Kong responses don't use the {code, data} envelope our services use
    if (res.status === 429) {
        throw new Error("Too many requests. Please slow down and try again.");
    }
    if (!res.ok && json.code === undefined) {
        throw new Error(json.message || `Request failed (${res.status})`);
    }

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
 * Render a buyer switcher dropdown into #buyer-switcher.
 * Saves selection to localStorage and reloads the page.
 */
const AVATAR_COLORS = ["user-avatar-blue", "user-avatar-purple", "user-avatar-teal", "user-avatar-orange", "user-avatar-green"];

function avatarColor(id) {
    return AVATAR_COLORS[id % AVATAR_COLORS.length];
}

function initBuyerSwitcher() {
    const container = document.getElementById("buyer-switcher");
    if (!container) return;

    const current = CONFIG.BUYERS.find(b => b.id === CONFIG.BUYER_ID) || CONFIG.BUYERS[0];
    const initial = current.name.charAt(0).toUpperCase();

    const wrapper = document.createElement("div");
    wrapper.className = "user-switcher";

    // Toggle button
    const toggle = document.createElement("button");
    toggle.className = "user-switcher-toggle";
    toggle.innerHTML = `<span class="user-avatar ${current.color || avatarColor(current.id)}">${initial}</span><span class="user-name">${current.name}</span><i data-lucide="chevron-down" class="user-chevron"></i>`;

    // Dropdown menu
    const menu = document.createElement("div");
    menu.className = "user-switcher-menu";

    CONFIG.BUYERS.forEach(b => {
        const item = document.createElement("button");
        item.className = "user-switcher-item" + (b.id === CONFIG.BUYER_ID ? " active" : "");
        const bInitial = b.name.charAt(0).toUpperCase();
        item.innerHTML = `<span class="user-avatar user-avatar-sm ${b.color || avatarColor(b.id)}">${bInitial}</span>${b.name}`;
        item.addEventListener("click", () => {
            if (b.id !== CONFIG.BUYER_ID) {
                localStorage.setItem("buyerId", b.id);
                window.location.reload();
            }
            menu.classList.remove("show");
        });
        menu.appendChild(item);
    });

    toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        menu.classList.toggle("show");
    });

    document.addEventListener("click", () => menu.classList.remove("show"));

    wrapper.appendChild(toggle);
    wrapper.appendChild(menu);
    container.appendChild(wrapper);
    refreshIcons();
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
 * Buyer-contextual listing status label.
 * Shows "Won" or "Outbid" for SOLD listings based on winningBuyerId.
 */
function buyerStatusLabel(listing, buyerId) {
    if (!listing) return "Unknown";
    switch (listing.status) {
        case "SCHEDULED": return "Upcoming";
        case "ACTIVE": return "Live";
        case "CLOSED_PENDING_PAYMENT":
            return listing.winningBuyerId === buyerId ? "Awaiting Payment" : "Processing";
        case "SOLD":
            return listing.winningBuyerId === buyerId ? "Won" : "Outbid";
        case "FAILED_NO_ELIGIBLE_BIDDER": return "No Winner";
        default: return listing.status;
    }
}

/**
 * Buyer-contextual listing status badge class.
 */
function buyerStatusBadgeClass(listing, buyerId) {
    if (!listing) return "badge-status-default";
    switch (listing.status) {
        case "SCHEDULED": return "badge-status-scheduled";
        case "ACTIVE": return "badge-status-active";
        case "CLOSED_PENDING_PAYMENT":
            return listing.winningBuyerId === buyerId ? "badge-status-active" : "badge-status-closed-pending";
        case "SOLD":
            return listing.winningBuyerId === buyerId ? "badge-status-active" : "badge-status-failed";
        case "FAILED_NO_ELIGIBLE_BIDDER": return "badge-status-failed";
        default: return "badge-status-default";
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

/**
 * Format a duration in ms as a human-readable relative string.
 * e.g. "2h 15m", "3d 1h", "45m", "30s"
 */
function formatRelativeDuration(ms) {
    const abs = Math.abs(ms);
    const totalSec = Math.floor(abs / 1000);
    const d = Math.floor(totalSec / 86400);
    const h = Math.floor((totalSec % 86400) / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    if (d > 0) return `${d}d ${h}h`;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m`;
    return `${s}s`;
}

/**
 * Format contextual time info for a listing based on its status.
 * Returns a single human-readable string like "Starts in 2h · Ends in 1d 3h" or "Ended 45m ago".
 */
function formatListingTime(listing) {
    if (listing.listingType !== "AUCTION" || !listing.startTime || !listing.endTime) return "";
    const now = new Date();
    const start = parseUtcDate(listing.startTime);
    const end = parseUtcDate(listing.endTime);

    if (listing.status === "SCHEDULED") {
        return `Starts in ${formatRelativeDuration(start - now)} · Ends in ${formatRelativeDuration(end - now)}`;
    } else if (listing.status === "ACTIVE") {
        if (end > now) return `Ends in ${formatRelativeDuration(end - now)}`;
        return `Ended ${formatRelativeDuration(now - end)} ago`;
    } else {
        return `Ended ${formatRelativeDuration(now - end)} ago`;
    }
}
