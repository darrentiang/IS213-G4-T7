# Entry point for Process Payment composite service.
# Consumer-only — listens to offer.accepted and orchestrates
# the payment flow via HTTP calls to User and Payment services.

from app.consumer import start

if __name__ == "__main__":
    start()
