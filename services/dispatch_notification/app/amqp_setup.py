def setup(channel):
    channel.exchange_declare(
        exchange="market.events",
        exchange_type="topic",
        durable=True
    )

    # notif.bid: receives bid.placed events
    # Used for: outbid notification ("You've been outbid!")
    channel.queue_declare(queue="notif.bid", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="notif.bid",
        routing_key="bid.placed"
    )

    # notif.listing: receives listing.scheduled and listing.active events
    # binding key "listing.*" matches any routing key starting with "listing."
    # Used for: "Your auction is scheduled" and "Your auction is now LIVE" emails
    channel.queue_declare(queue="notif.listing", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="notif.listing",
        routing_key="listing.*"
    )

    print("AMQP setup complete: dispatch_notification queues declared")
