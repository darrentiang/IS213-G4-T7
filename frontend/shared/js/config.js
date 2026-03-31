const GATEWAY_URL = `http://${window.location.hostname}:8000`;

const CONFIG = {
    LISTING_API: GATEWAY_URL,
    BID_API: GATEWAY_URL,
    OFFER_API: GATEWAY_URL,
    USER_API: GATEWAY_URL,
    PAYMENT_API: GATEWAY_URL,

    // Hardcoded seller ID
    SELLER_ID: 1,

    // Buyer ID from localStorage, default to Bob (2)
    BUYER_ID: parseInt(localStorage.getItem("buyerId")) || 2,

    // Available buyer accounts for the switcher
    BUYERS: [
        { id: 2, name: "Bob Lim" },
        { id: 3, name: "Charlie Ng" },
    ],
};
