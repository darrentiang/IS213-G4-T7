"""
Declares RabbitMQ exchanges and queues used by the WebSocket server.
"""


def setup(channel):
    # Topic exchange for all business events
    channel.exchange_declare(
        exchange="market.events",
        exchange_type="topic",
        durable=True
    )

    # ws.bid_updates: consumes bid.placed events and pushes to WebSocket clients
    channel.queue_declare(queue="ws.bid_updates", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="ws.bid_updates",
        routing_key="bid.placed"
    )

    print("AMQP setup complete: ws_server queues declared")
