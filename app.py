#!venv/bin/python
import argparse
import logging
import asyncio
import motor.motor_asyncio

import crypt
from config import config, logger_configure
from queue_connect import QueueListener, QueuePublisher
from payment_processing import Processing

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
            await task


def create_app(loop=None):
    """
    Create server application and all necessary services.
    :param loop: async main loop
    """

    config['RSA_KEY'] = crypt.create_rsa_key()

    app = Application(loop=loop)
    app['config'] = config

    motor_client = motor.motor_asyncio.AsyncIOMotorClient()
    db = motor_client[config['DB_NAME']]
    app['db'] = db

    queue_publisher = QueuePublisher(connect_parameters=config)
    queue_publisher.start()
    app.on_shutdown.append(queue_publisher.close())

    trans_status_handler = queue_publisher.get_sender_for_queue(config['QUEUE_TRANS_STATUS'])

    processing = Processing(db=db, results_handler=trans_status_handler)

    queue_listener = QueueListener(
        queue_handlers=[
            (config['QUEUE_TRANS_FOR_PROCESSING'], processing.transaction_handler),
            (config['QUEUE_3D_SECURE_RESULT'], processing.response_3d_secure_handler),
        ],
        connect_parameters=config
    )
    queue_listener.start()
    app.on_shutdown.append(queue_listener.close())

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

    parser = argparse.ArgumentParser(description='XOPay Processing Service.', allow_abbrev=False)
    parser.add_argument('--config', default='debug', help='load config: [debug, test, production] (default "debug")')

    args = parser.parse_args()
    config.load_config(args.config)

    logger_configure(config)

    application = create_app()
    run_app(application)
