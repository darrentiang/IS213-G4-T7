# IS213-G4-T7

## Services

### Atomic Services (Flask + MySQL)

| Service | Port | Database |
|---------|------|----------|
| Listing | 5001 | listing_db | 
| Bid | 5002 | bid_db | 
| Offer | 5003 | offer_db | 
| User | 5004 | user_db |
| Payment | 5005 | payment_db | 

### Composite Services (Flask, no database)

| Service | Port | Purpose | 
|---------|------|---------|
| Close Auction | 5006 | US2 | 
| Process Payment | 5007 | US3 | 

### Other

| Component | Technology | Notes |
|-----------|-----------|-------|
| Notification | OutSystems | TBD: may be User Service instead |
| KONG | API Gateway | Routing + rate limiting on POST /bids |
