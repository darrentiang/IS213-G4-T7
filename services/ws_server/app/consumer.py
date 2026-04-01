"""
WebSocket server + AMQP consumer — US2 Diagram 1 (BG step).
Consumes bid.placed from ws.bid_updates and broadcasts to all WebSocket
clients subscribed to that listing.

Architecture:
  - pika consumer runs in a background thread (blocking, matches repo pattern)
  - asyncio event loop runs the WebSocket server on port 6000
  - bridge: asyncio.run_coroutine_threadsafe() pushes messages across threads
"""

import asyncio
import json
import threading
import time
import websockets
from os import environ

from app.amqp_lib import connect
from app import amqp_setup

amqp_host = environ.get("RABBITMQ_HOST", "localhost")
amqp_port = int(environ.get("RABBITMQ_PORT", 5672))

# { listing_id (str): set of websocket connections }
_subscribers: dict = {}

# asyncio event loop shared between the consumer thread and the WS server
_loop: asyncio.AbstractEventLoop | None = None


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------

async def _ws_handler(websocket):
    """
    Handles a WebSocket connection lifecycle.
    Client sends:  {"action": "subscribe", "listingId": 123}
    Server pushes: {"event": "bid.placed", "listingId": "123", "amount": 99.99, "buyerId": 2}
    """
    listing_id = None
    try:
        async for raw in websocket:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if payload.get("action") == "subscribe":
                listing_id = str(payload["listingId"])
                _subscribers.setdefault(listing_id, set()).add(websocket)
                await websocket.send(json.dumps({
                    "status": "subscribed",
                    "listingId": listing_id
                }))
                print(f"[ws] Client subscribed to listing {listing_id} "
                      f"({len(_subscribers[listing_id])} subscriber(s))")
    finally:
        if listing_id:
            _subscribers.get(listing_id, set()).discard(websocket)
            print(f"[ws] Client disconnected from listing {listing_id}")


# ---------------------------------------------------------------------------
# Broadcast helper (runs on asyncio loop)
# ---------------------------------------------------------------------------

async def _broadcast(listing_id: str, data: dict):
    conns = _subscribers.get(listing_id, set()).copy()
    if not conns:
        return

    msg = json.dumps(data)
    dead = set()
    for ws in conns:
        try:
            await ws.send(msg)
        except Exception:
            dead.add(ws)

    for ws in dead:
        _subscribers.get(listing_id, set()).discard(ws)

    print(f"[ws] Broadcast to {len(conns) - len(dead)} client(s) for listing {listing_id}")


# ---------------------------------------------------------------------------
# AMQP consumer (runs in background thread)
# ---------------------------------------------------------------------------

def _handle_bid_placed(channel, method, properties, body):
    """Called by pika when a bid.placed message arrives on ws.bid_updates."""
    data = json.loads(body)
    listing_id = str(data.get("listingId"))
    print(f"[amqp] bid.placed received — listing {listing_id}, amount={data.get('amount')}")

    if _loop:
        asyncio.run_coroutine_threadsafe(
            _broadcast(listing_id, {
                "event": "bid.placed",
                "listingId": listing_id,
                "amount": data.get("amount"),
                "buyerId": data.get("buyerId"),
            }),
            _loop
        )

    channel.basic_ack(delivery_tag=method.delivery_tag)


def _run_consumer():
    """Runs the pika consumer in a background thread. Auto-reconnects on failure."""
    while True:
        try:
            connection, channel = connect(amqp_host, amqp_port)
            amqp_setup.setup(channel)
            print("[amqp] WebSocket server listening on ws.bid_updates...")
            channel.basic_consume(
                queue="ws.bid_updates",
                on_message_callback=_handle_bid_placed,
                auto_ack=False
            )
            channel.start_consuming()
        except Exception as e:
            print(f"[amqp] Consumer error: {e}, reconnecting in 2s...")
            time.sleep(2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _start_ws_server():
    print("[ws] WebSocket server running on port 6000...")
    async with websockets.serve(_ws_handler, "0.0.0.0", 6000):
        await asyncio.Future()  # run forever


def start():
    global _loop

    # Create the event loop before starting the consumer thread so that
    # _handle_bid_placed can safely call run_coroutine_threadsafe().
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    consumer_thread = threading.Thread(target=_run_consumer, daemon=True)
    consumer_thread.start()

    _loop.run_until_complete(_start_ws_server())
