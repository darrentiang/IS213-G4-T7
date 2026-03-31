const GATEWAY_URL = `http://${window.location.hostname}:8000`;

const CONFIG = {
    LISTING_API: GATEWAY_URL,
    BID_API: GATEWAY_URL,
    OFFER_API: GATEWAY_URL,
    USER_API: GATEWAY_URL,
    PAYMENT_API: GATEWAY_URL,

    // Hardcoded user IDs — actual names/emails fetched from User Service
    SELLER_ID: 1,
    BUYER_ID: 2,
};
