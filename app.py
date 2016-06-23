#!venv/bin/python
import logging
import asyncio
import motor.motor_asyncio

import crypt
from config import config
from processing.processing import Processing

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
        if self.on_shutdown:
            shut_futures = [shut_call(self) for shut_call in self.on_shutdown]
            await asyncio.wait(shut_futures)


def create_app():
    """Create and run all processing services."""
    app = Application()
    app['config'] = config

    motor_client = motor.motor_asyncio.AsyncIOMotorClient()
    db = motor_client[app.config['DB_NAME']]
    app['db'] = db

    # FIXME: make rsa_setup async
    crypt.rsa_setup()

    processing = Processing(db=db, loop=app.loop)
    processing.init()
    app['processing'] = processing

    return app


async def shutdown(app):
    """
    Close connections, stop daemons and all process.
    :param app: service application
    """
    _log.info('Stopping XOPay Processing Service...')

    processing = app.get('processing')
    if processing:
        await processing.stop()

    _log.info('Shutdown tasks')
    tasks = asyncio.Task.all_tasks()
    if tasks:
        for task in tasks:
            task.cancel()
        try:
            await asyncio.wait(tasks)
        except Exception:
            pass

    _log.info('XOPay Processing Service Stopped!')


def run_app(app):
    """
    Run application infinite loop.
    :param app: service application
    """
    loop = app.loop
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(app.shutdown())
    loop.close()


if __name__ == "__main__":

    application = create_app()
    application.on_shutdown.append(shutdown)

    _log.info('Starting XOPay Processing Service...')
    if application.config['DEBUG']:
        _log.warning('Debug mode is active!')

    run_app(application)
