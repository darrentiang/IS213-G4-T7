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

    # market.timers.close: holds auction.close messages until TTL expires,
    # then dead-letters to market.dlq.close
    channel.queue_declare(
        queue="market.timers.close",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": "market.dlq.close"
        }
    )

    # market.dlq.close: receives expired auction.close messages
    # Close Auction consumes from this queue
    channel.queue_declare(
        queue="market.dlq.close",
        durable=True
    )

    print("AMQP setup complete: close_auction queues declared")
