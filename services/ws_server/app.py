# Entry point for WebSocket server.
# Consumer-only — listens to ws.bid_updates and pushes live bid updates
# to connected WebSocket clients.

from app.consumer import start

if __name__ == "__main__":
    start()
