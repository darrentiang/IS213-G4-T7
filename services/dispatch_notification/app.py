# Entry point for Dispatch Notification service.
# Unlike atomic services, there is no Flask HTTP server here —
# this service only listens to RabbitMQ and reacts to events.

from app.consumer import start

if __name__ == "__main__":
    start()
