# Entry point for Close Auction composite service.
# Consumer-only — listens to market.dlq.close and orchestrates
# the auction close + payment cascade flow via HTTP calls.

from app.consumer import start

if __name__ == "__main__":
    start()
