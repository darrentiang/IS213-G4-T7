def setup(channel):
    channel.exchange_declare(
        exchange="market.events",
        exchange_type="topic",
        durable=True
    )

    channel.queue_declare(queue="notif.bid", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="notif.bid",
        routing_key="bid.placed"
    )

    channel.queue_declare(queue="ws.bid_updates", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="ws.bid_updates",
        routing_key="bid.placed"
    )

    print("AMQP setup complete: bid exchanges and queues declared")
