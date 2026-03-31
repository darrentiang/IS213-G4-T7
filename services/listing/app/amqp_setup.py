"""
Declares RabbitMQ exchanges and queues used by the Listing service.
Run once on startup to ensure infrastructure exists.
"""


def setup(channel):
    # Topic exchange for all business events
    channel.exchange_declare(
        exchange="market.events",
        exchange_type="topic",
        durable=True
    )

    # DLQ queues for timer expiry (unique per-listing timer queues are
    # created dynamically at publish time — see routes.py and consumer.py)
    channel.queue_declare(queue="market.dlq.start", durable=True)
    channel.queue_declare(queue="market.dlq.close", durable=True)

    # listing.sold queue: listens for payment.success to mark listing SOLD
    channel.queue_declare(queue="listing.sold", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="listing.sold",
        routing_key="payment.success"
    )

    # notif.listing queue: Dispatch Notification subscribes to listing.*
    channel.queue_declare(queue="notif.listing", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="notif.listing",
        routing_key="listing.*"
    )

    print("AMQP setup complete: exchanges and queues declared")
