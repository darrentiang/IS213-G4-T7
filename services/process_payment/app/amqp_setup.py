"""
Declares RabbitMQ exchanges and queues used by the Process Payment service.
"""


def setup(channel):
    # Topic exchange for all business events
    channel.exchange_declare(
        exchange="market.events",
        exchange_type="topic",
        durable=True
    )

    # process_payment.offer_accepted: consumes offer.accepted events
    channel.queue_declare(queue="process_payment.offer_accepted", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="process_payment.offer_accepted",
        routing_key="offer.accepted"
    )

    print("AMQP setup complete: process_payment queues declared")
