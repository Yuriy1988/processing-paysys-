#!venv/bin/python
import logging
import asyncio
import motor.motor_asyncio

import crypt
from config import config
from queue_connect import QueueListener, QueuePublisher
from processing import Processing, handle_transaction

__author__ = 'Kostel Serhii'


_log = logging.getLogger('xop.main')


class Application(dict):
    """ Dict like application class."""

    def __init__(self, loop=None):
        super().__init__()
        self._loop = loop or asyncio.get_event_loop()
        self.on_shutdown = []

    def __repr__(self):
        return "<Application>"

    def __getattr__(self, item):
        if item not in dir(self):
            return self.get(item)
        else:
            return super().__getattribute__(item)

    @property
    def loop(self):
        return self._loop

    async def shutdown(self):
        for task in self.on_shutdown:
            await task()


def create_app():
    """Create and run all processing services."""

    config['RSA_KEY'] = crypt.create_rsa_key()

    app = Application()
    app['config'] = config

    motor_client = motor.motor_asyncio.AsyncIOMotorClient()
    db = motor_client[config['DB_NAME']]
    app['db'] = db

    queue_listener = QueueListener(
        queue_handlers=[
            (config['QUEUE_TRANS_FOR_PROCESSING'], handle_transaction),
        ],
        connect_parameters=config
    )
    queue_listener.start()
    app.on_shutdown.append(queue_listener.close())
    app['queue_listener'] = queue_listener

    queue_publisher = QueuePublisher(connect_parameters=config)
    queue_publisher.start()
    app.on_shutdown.append(queue_publisher.close())
    app['queue_publisher'] = queue_publisher

    processing = Processing(db=db, output_queue=queue_publisher, loop=app.loop)
    processing.init()
    app.on_shutdown.append(processing.stop())
    app['processing'] = processing

    return app


async def shutdown_tasks():
    """Shutdown unfinished async tasks."""
    _log.info('Shutdown tasks')

    tasks = asyncio.Task.all_tasks()
    if tasks:
        for task in tasks:
            task.cancel()
        try:
            await asyncio.wait(tasks)
        except Exception:
            pass


def run_app(app):
    """
    Run application infinite loop.
    :param app: service application
    """
    _log.info('Starting XOPay Processing Service...')
    if app.config['DEBUG']:
        _log.warning('Debug mode is active!')

    loop = app.loop
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _log.info('Stopping XOPay Processing Service...')
        loop.run_until_complete(app.shutdown())
        loop.run_until_complete(shutdown_tasks())
    loop.close()

    _log.info('XOPay Processing Service Stopped!')


if __name__ == "__main__":

    application = create_app()
    run_app(application)
