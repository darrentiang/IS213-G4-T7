"""
Declares RabbitMQ exchanges and queues used by the Close Auction service.
"""


def setup(channel):
    # Topic exchange for all business events
    channel.exchange_declare(
        exchange="market.events",
        exchange_type="topic",
        durable=True
    )

    # market.dlq.close: receives expired auction.close messages
    # (unique per-listing timer queues dead-letter here — see listing service)
    channel.queue_declare(queue="market.dlq.close", durable=True)

    print("AMQP setup complete: close_auction queues declared")
