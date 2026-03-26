import json
import time
import pika


def connect(hostname, port, max_retries=12, retry_interval=5):
    retries = 0
    while retries < max_retries:
        retries += 1
        try:
            print(f"Connecting to RabbitMQ at {hostname}:{port} (attempt {retries})...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=hostname,
                    port=port,
                    heartbeat=60,
                    blocked_connection_timeout=300,
                )
            )
            print("Connected to RabbitMQ")
            channel = connection.channel()
            return connection, channel
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Connection failed: {e}")
            print(f"Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)

    raise Exception(f"Could not connect to RabbitMQ after {max_retries} attempts")
