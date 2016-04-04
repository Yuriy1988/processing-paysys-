import pika
import logging
from tornado import gen
from tornado.concurrent import Future
from pika.adapters.tornado_connection import TornadoConnection

import config


log = logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT)


class ConsumingClient:
    def __init__(self, url='', queue_name="default"):
        self.queue_name = queue_name
        self.url = url
        self.bind_future = Future()
        self.message_future = Future()

    def connect(self):
        self.connection = TornadoConnection(parameters=pika.URLParameters(self.url), on_open_callback=self.on_connected)
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

    def on_queue_declared(self, frame):
        self.bind_future.set_result(True)
        self.channel.basic_consume(self.handle_delivery, queue=self.queue_name, no_ack=True)

    def handle_delivery(self, channel, method, header, body):
        self.message_future.set_result(body)

    @gen.coroutine
    def get_message(self):
        message = yield self.message_future
        self.message_future = Future()
        return message


class PublishingClient:

    def __init__(self, url="", queue_name="default"):

        self.queue_name = queue_name
        self.channel = None
        self.url = url
        self.bind_future = Future()
        self.publish_future = Future()
        self.connection = None

    def connect(self):
        if self.connection:
            self.bind_future.set_result(True)
            return self.bind_future
        self.connection = TornadoConnection(parameters=pika.URLParameters(self.url), on_open_callback=self.on_connected)
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

    def on_queue_declared(self, frame):
        self.bind_future.set_result(True)

    def publish(self, body):
        self._publish(self.queue_name, body)
        return self.publish_future

    def _publish(self, queue, body):
        properties = pika.BasicProperties(content_type='text/plain')
        a = self.channel.basic_publish('', queue, body, properties)
        if not self.publish_future.done():
            self.publish_future.set_result(True)
        return self.publish_future

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        self.connection.close()
