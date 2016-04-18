import pika
import logging
import json
from pika.adapters.tornado_connection import TornadoConnection
from tornado.concurrent import Future

import config


log = logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)


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

    def __init__(self, ioloop):
        self.consumer = _ConsumingAsyncClient()
        ioloop.add_callback(self._main_loop)

    async def _main_loop(self):
        try:
            await self.consumer.connect()
        except Exception as e:
            print(e)

    async def get(self):
        message = await self.consumer.get_message()
        return json.loads(message.decode())


class RabbitPublisher:

    def put(self, element):
        queue = config.OUTCOME_QUEUE_NAME
        body = json.dumps(element)
        params = _get_connection_parameters()
        publish_properties = pika.BasicProperties(content_type='text/plain', delivery_mode=2)

        with pika.BlockingConnection(params) as connection:
            channel = connection.channel()
            channel.queue_declare(queue=queue, durable=True, exclusive=False, auto_delete=False)
            channel.basic_publish(exchange='', routing_key=queue, body=body, properties=publish_properties)


class _ConsumingAsyncClient:
    def __init__(self):
        self.bind_future = Future()
        self.message_future = Future()
        self.channel = None
        self.connection = None

    def connect(self):
        params = _get_connection_parameters()
        self.connection = TornadoConnection(parameters=params, on_open_callback=self.on_connected)
        return self.bind_future

    def on_connected(self, connection):
        self.connection.channel(self.on_channel_open)

    def on_channel_open(self, channel):
        self.channel = channel
        channel.queue_declare(queue=config.INCOME_QUEUE_NAME,
                              durable=True,
                              exclusive=False,
                              auto_delete=False,
                              callback=self.on_queue_declared)

    def on_queue_declared(self, frame):
        self.bind_future.set_result(True)
        self.channel.basic_consume(self.handle_delivery, queue=config.INCOME_QUEUE_NAME, no_ack=True)

    def handle_delivery(self, channel, method, header, body):
        self.message_future.set_result(body)

    async def get_message(self):
        message = await self.message_future
        self.message_future = Future()
        return message
