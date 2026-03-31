const CONFIG = {
    LISTING_API: "http://localhost:5001",
    BID_API: "http://localhost:5002",
    OFFER_API: "http://localhost:5003",
    USER_API: "http://localhost:5004",
    PAYMENT_API: "http://localhost:5005",

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
