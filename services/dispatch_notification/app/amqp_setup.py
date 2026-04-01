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

    # notif.auction: receives auction.no_eligible_bidders events
    # Used for: "No eligible bidders" email to seller
    channel.queue_declare(queue="notif.auction", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="notif.auction",
        routing_key="auction.no_eligible_bidders"
    )

    # notif.payment: receives payment.success and payment.failed events
    # Used for: "Payment confirmed!" / "Payment failed" emails to buyer + seller
    channel.queue_declare(queue="notif.payment", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="notif.payment",
        routing_key="payment.*"
    )

    # notif.offer: receives offer.created, offer.countered, offer.accepted, offer.rejected events
    # binding key "offer.*" matches any routing key starting with "offer."
    channel.queue_declare(queue="notif.offer", durable=True)
    channel.queue_bind(
        exchange="market.events",
        queue="notif.offer",
        routing_key="offer.*"
    )

    print("AMQP setup complete: dispatch_notification queues declared")
