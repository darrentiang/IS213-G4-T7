"""
Declares RabbitMQ exchanges and queues used by the Offer service.
"""


def setup(channel):
    # Topic exchange for all business events
    channel.exchange_declare(
        exchange="market.events",
        exchange_type="topic",
        durable=True
    )

    # offer.payment_failed: consumes payment.failed events
    channel.queue_declare(queue="offer.payment_failed", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="offer.payment_failed",
        routing_key="payment.failed"
    )

    print("AMQP setup complete: offer queues declared")
