import json
import logging
import aioamqp
import asyncio
from json.decoder import JSONDecodeError

from config import config


_log = logging.getLogger('xop.queue')


class _QueueConnect(object):
    """
    Async connector to RabbitMQ.
    * For Python 3.5 or higher.
    """

    MIN_RECONNECT_TIMEOUT_SEC = 1
    MAX_RECONNECT_TIMEOUT_SEC = 300

    _default_declare_params = dict(
        passive=False,
        durable=True,
        exclusive=False,
        auto_delete=False,
        nowait=False
    )

    def __init__(self, connect_parameters=None):
        """
        Create RabbitMQ Async Queue Connection
        :param dict connect_parameters: dict with keys:
            QUEUE_HOST, QUEUE_PORT, QUEUE_USERNAME, QUEUE_PASSWORD, QUEUE_VIRTUAL_HOST
        """
        self._connect_params = connect_parameters

        self._queue_channels = dict()

        self._waiter = asyncio.Event()
        self._transport = None
        self._protocol = None

        self._closing = False

        self._reconnect_timeout_sec = self.MIN_RECONNECT_TIMEOUT_SEC

    def _get_connect_parameters(self):
        """Map connect parameters to aioamqp connect arguments."""
        return dict(
            host=self._connect_params['QUEUE_HOST'],
            port=self._connect_params['QUEUE_PORT'],
            login=self._connect_params['QUEUE_USERNAME'],
            password=self._connect_params['QUEUE_PASSWORD'],
            virtualhost=self._connect_params['QUEUE_VIRTUAL_HOST']
        )

    async def connect(self):
        """
        Create async connection to the RabbitMQ, chanel and queue.
        Start unfinished loop.
        Try to reconnect after connection error.
        """
        connect_params = self._get_connect_parameters()

        while not self._closing:

            await asyncio.sleep(self._get_reconnect_timeout())

            try:
                self._transport, self._protocol = await aioamqp.connect(**connect_params)
            except aioamqp.AioamqpException as err:
                _log.error("Queue connection error: %r \nReconnecting...", err)
                continue

            _log.info('Connected to the RabbitMQ')

            try:
                await self._chanel_connection()
            except aioamqp.AioamqpException as err:
                _log.error("Chanel connection error: %r \nReconnecting...", err)
                continue

            self._reset_reconnect_timeout()

            _log.info('Start queue connection loop')
            await self._waiter.wait()

        logging.info('Queue connection loop has been finished!')

    async def close(self):
        """ Close connection to the RabbitMQ """
        _log.info('Close queue connection')
        self._closing = True
        self._waiter.set()

        if self._protocol:
            await self._protocol.close()

        if self._transport:
            self._transport.close()

    async def clean(self):
        """Delete all registered channels queue."""
        delete_queues = [channel.queue_delete(queue_name) for queue_name, channel in self._queue_channels.items()]
        await asyncio.wait(delete_queues)

    async def _get_or_declare_channel(self, queue_name):
        """
        Get or declare (if not registered) and return chanel for queue.
        :param queue_name: name of the queue to register
        """
        channel = self._queue_channels.get(queue_name)

        if channel is None:
            channel = await self._protocol.channel()
            await channel.queue_declare(queue_name=queue_name, durable=True)
            self._queue_channels[queue_name] = channel

        return channel

    async def _chanel_connection(self):
        """
        Async chanel connection method.
        Add here connection to the chanel (or many channels),
        declare and bind to the queue and/or exchange,
        start basic operations.
        """
        raise NotImplementedError('Queue chanel not created')

    def _get_reconnect_timeout(self):
        """
        This function double reconnection timeout on every request
        to protect from frequent attempts to connect."""
        timeout_sec = self._reconnect_timeout_sec
        self._reconnect_timeout_sec = min(self._reconnect_timeout_sec * 2, self.MAX_RECONNECT_TIMEOUT_SEC)
        return timeout_sec

    def _reset_reconnect_timeout(self):
        """ Set reconnection timeout to start value. """
        self._reconnect_timeout_sec = self.MIN_RECONNECT_TIMEOUT_SEC


class QueueListener(_QueueConnect):
    """
    Async RabbitMQ listener (consumer)
    """
    def __init__(self, queue_handlers, connect_parameters=None):
        """
        Create RabbitMQ Async Queue Listener
        :param list queue_handlers: list with tuples (queue_name, async on_msg_callback)
        :param dict connect_parameters: dict with keys: host, port, login, password, virtualhost
        """
        self._queue_handlers = queue_handlers
        super().__init__(connect_parameters)

    async def _chanel_connection(self):
        """ Declare queues and register on message callback handlers """

        if not self._transport or not self._protocol:
            raise Exception('Queue connection missing')

        for queue_name, on_msg_callback in self._queue_handlers:
            callback = self._wrap_on_msg_callback_with_ack(on_msg_callback)

            channel = await self._get_or_declare_channel(queue_name=queue_name)
            await channel.basic_consume(callback, queue_name=queue_name)

    @staticmethod
    def _wrap_on_msg_callback_with_ack(callback):
        """
        Get on message callback function, make it async and
        wrap with basic queue ack after function end.
        Decode queue message body to json dict.

        :param callback: on message handler
        :return: async callback with ack
        """
        if not asyncio.iscoroutinefunction(callback):
            callback = asyncio.coroutine(callback)

        async def _on_message(channel, body, envelope, properties):
            _log.debug('Received message #%s: %r', envelope.delivery_tag, body)

            try:
                message = json.loads(body.decode())
            except (JSONDecodeError, TypeError) as err:
                _log.error('Wrong queue message [%r]: %r', body, err)
            else:
                await callback(message)

            _log.debug('Send message #%s ack', envelope.delivery_tag)
            await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)

        return _on_message

    def start(self):
        """Add connection into loop."""
        _log.info('Start queue listener')
        asyncio.ensure_future(self.connect())


class QueuePublisher(_QueueConnect):
    """
    Async RabbitMQ publisher
    """
    def __init__(self, connect_parameters=None):
        """
        Create RabbitMQ Async Queue Publisher
        :param dict connect_parameters: dict with keys: host, port, login, password, virtualhost
        """
        super().__init__(connect_parameters)
        self._connection_waiter = asyncio.Event()

    async def _chanel_connection(self):
        """
        Wait for queue connection.
        Publisher channels will be registered lazily before message send."""
        if not self._transport or not self._protocol:
            raise Exception('Queue connection missing')

        self._connection_waiter.set()

    async def send(self, queue_name, message):
        """
        Send message to queue.
        :param queue_name: name of the queue to send message
        :param message: dict or str with information to send
        """
        await self._connection_waiter.wait()

        body = json.dumps(message) if isinstance(message, dict) else message

        _log.debug('Send message to queue [%s]: %s', queue_name, str(message))

        channel = await self._get_or_declare_channel(queue_name)
        await channel.basic_publish(payload=body, routing_key=queue_name, exchange_name='')

    def get_sender_for_queue(self, queue_name):
        """
        Fabric to create sender for queue (like partial method).
        :param queue_name: name of the queue
        :return: async sender with predefined queue name
        """
        async def queue_sender(message):
            await self.send(queue_name, message)

        return queue_sender

    def start(self):
        """Add connection into loop."""
        _log.info('Start queue publisher')
        asyncio.ensure_future(self.connect())


if __name__ == '__main__':

    LOG_FORMAT = '%(levelname)-6.6s | %(name)-12.12s | %(asctime)s | %(message)s'
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
    log_handler.setFormatter(log_formatter)
    root_logger = logging.getLogger('')
    root_logger.addHandler(log_handler)
    root_logger.setLevel('DEBUG')

    QUEUE_NAME = 'test'

    async def on_message(body):
        logging.info('Get message: %r', body)

    async def sender(pusher, num=5):
        for i in range(num):
            await pusher('Message #%d' % i)
            await asyncio.sleep(1)

    loop = asyncio.get_event_loop()

    queue_listener = QueueListener(queue_handlers=[(QUEUE_NAME, on_message)], connect_parameters=config)
    queue_listener.start()

    queue_publisher = QueuePublisher(connect_parameters=config)
    queue_publisher.start()

    logging.info(' [*] Start')
    try:
        loop.run_until_complete(sender(queue_publisher.get_sender_for_queue(QUEUE_NAME)))
    except KeyboardInterrupt:
        pass
    finally:
        logging.info(' [*] Stop queue daemon')
        loop.run_until_complete(queue_publisher.close())
        loop.run_until_complete(queue_listener.close())

        loop.close()
