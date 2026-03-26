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

    # market.timers.start: holds auction.start messages until TTL expires,
    # then dead-letters to market.dlq.start (consumed by Listing)
    channel.queue_declare(
        queue="market.timers.start",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "market.dlq.start"
        }
    )

    # market.dlq.start: receives expired auction.start messages
    channel.queue_declare(
        queue="market.dlq.start",
        durable=True
    )

    # market.timers.close: holds auction.close messages until TTL expires,
    # then dead-letters to market.dlq.close (consumed by Close Auction)
    channel.queue_declare(
        queue="market.timers.close",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "market.dlq.close"
        }
    )

    # market.dlq.close: receives expired auction.close messages
    channel.queue_declare(
        queue="market.dlq.close",
        durable=True
    )

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
