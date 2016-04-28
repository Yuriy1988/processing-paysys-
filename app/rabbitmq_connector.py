import json
import pika
import logging
from pika.adapters.tornado_connection import TornadoConnection
from tornado.concurrent import Future

from config_loader import config


def _get_connection_parameters():
    """
    Return pika connection parameters object.
    """
    return pika.ConnectionParameters(
        host=config.RABBIT_HOST,
        port=config.RABBIT_PORT,
        virtual_host=config.RABBIT_VIRTUAL_HOST,
        credentials=pika.credentials.PlainCredentials(
            username=config.RABBIT_USERNAME,
            password=config.RABBIT_PASSWORD,
        )
    )


class RabbitAsyncConsumer:
    """Wraps RabbitMQ functionality"""

    def __init__(self, ioloop, queue_name):
        self.consumer = _ConsumingAsyncClient(queue_name)
        ioloop.add_callback(self._main_loop)

    async def _main_loop(self):
        try:
            await self.consumer.connect()
        except Exception as e:
            logging.error(e)

    async def get(self):
        message = await self.consumer.get_message()
        return json.loads(message.decode())

    def close_connection(self):
        self.consumer.close_connection()


class RabbitConsumer:

    def __init__(self, queue_name):
        self.queue_name = queue_name

    def get(self):
        connection = pika.BlockingConnection(_get_connection_parameters())

        channel = connection.channel()

        channel.queue_declare(queue=self.queue_name, durable=True)

        result = None

        def callback(ch, method, properties, body):
            result = body
            channel.stop_consuming()

        channel.basic_consume(callback,
                              queue=self.queue_name,
                              no_ack=True)

        channel.start_consuming()
        return result


class RabbitPublisher:

    def __init__(self, queue_name):
        self.queue_name = queue_name

    def put(self, element):
        body = json.dumps(element)
        params = _get_connection_parameters()
        publish_properties = pika.BasicProperties(content_type='text/plain', delivery_mode=2)

        with pika.BlockingConnection(params) as connection:
            channel = connection.channel()
            channel.queue_declare(queue=self.queue_name, durable=True, exclusive=False, auto_delete=False)
            logging.info("RabbitMQ PUB: " + self.queue_name + " queue declared")
            channel.basic_publish(exchange='', routing_key=self.queue_name, body=body, properties=publish_properties)
            logging.info("RabbitMQ PUB: sent: " + body)


class _ConsumingAsyncClient:
    def __init__(self, queue_name):
        self.queue_name = queue_name
        self.bind_future = Future()
        self.message_future = Future()
        self.channel = None
        self.connection = None

    def connect(self):
        params = _get_connection_parameters()
        logging.info("RabbitMQ CNS: Connecting...")
        self.connection = TornadoConnection(parameters=params, on_open_callback=self.on_connected)
        logging.info("RabbitMQ CNS: Connected!")
        return self.bind_future

    def on_connected(self, connection):
        self.connection.channel(self.on_channel_open)

    def on_channel_open(self, channel):
        self.channel = channel
        channel.queue_declare(queue=self.queue_name,
                              durable=True,
                              exclusive=False,
                              auto_delete=False,
                              callback=self.on_queue_declared)
        logging.info("RabbitMQ CNS: " + config.INCOME_QUEUE_NAME + " queue declared")

    def on_queue_declared(self, frame):
        self.bind_future.set_result(True)
        self.channel.basic_consume(self.handle_delivery, queue=self.queue_name, no_ack=True)

    def handle_delivery(self, channel, method, header, body):
        self.message_future.set_result(body)

    async def get_message(self):
        message = await self.message_future
        self.message_future = Future()
        logging.info("RabbitMQ CNS: New message: " + str(message))
        return message

    def close_connection(self):
        self.connection.close()
