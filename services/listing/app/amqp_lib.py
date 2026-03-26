"""
Reusable AMQP connection and publishing functions for RabbitMQ.
Based on IS213 lab patterns.
"""

import json
import time
import pika


def connect(hostname, port, max_retries=12, retry_interval=5):
    """Connect to RabbitMQ broker with retry logic."""
    retries = 0

    while retries < max_retries:
        retries += 1
        try:
            print(f"Connecting to AMQP broker {hostname}:{port}...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=hostname,
                    port=port,
                    heartbeat=60,
                    blocked_connection_timeout=300,
                )
            )
            print("Connected to AMQP broker")
            channel = connection.channel()
            return connection, channel

        except pika.exceptions.AMQPConnectionError as e:
            print(f"Failed to connect: {e}")
            print(f"Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)

    raise Exception(f"Max {max_retries} retries exceeded")


def close(connection, channel):
    """Close the AMQP connection and channel."""
    channel.close()
    connection.close()


def is_connection_open(connection):
    """Check if the AMQP connection is still open."""
    try:
        connection.process_data_events()
        return True
    except pika.exceptions.AMQPError as e:
        print("AMQP Error:", e)
        return False


def publish_message(channel, exchange, routing_key, message, properties=None):
    """Publish a message to an exchange with a routing key."""
    channel.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=json.dumps(message),
        properties=properties or pika.BasicProperties(delivery_mode=2)
    )
    print(f"Published to {exchange or '(default)'} with key '{routing_key}': {message}")
