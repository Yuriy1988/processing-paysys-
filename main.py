import momoko
import logging
import tornado.web
import tornado.ioloop
import tornado.httpserver
from tornado.queues import PriorityQueue

import config
from processing.processing_daemon import AuthSourceHandler, AuthDestinationHandler, CaptureSourceHandler,\
    CaptureDestinationHandler, NewTransactionHandler
from processing import crypt


queues = {
    'auth_source': PriorityQueue(),
    'auth_destination': PriorityQueue(),
    'capture_source': PriorityQueue(),
    'capture_destination': PriorityQueue(),
    'void': PriorityQueue()
}


class Application(tornado.web.Application):
    """ Tornado server application. """

    def __init__(self):

        """ Configure handlers and settings. """
        handlers = []

        settings = dict(
            debug=True,
        )
        self.db = momoko.Pool(
            dsn='dbname={dbname} user={username} password={password} host={host} port={port}'.format(
                dbname=config.DB_NAME,
                username=config.DB_USER,
                password=config.DB_USER_PASSWORD,
                host=config.DB_HOST,
                port=config.DB_PORT
            ),
        )
        self.db.connect()

        super(Application, self).__init__(handlers, **settings)


def rsa_setup():
    if config.DEBUG:
        if crypt.is_debug_key_exists():
            config.RSA_KEY = crypt.debug_load_key()
        else:
            config.RSA_KEY = crypt.debug_generate()
    else:
        config.RSA_KEY = crypt.generate()
    crypt.update_public_key_on_client(config.RSA_KEY)


def main():
    logging.basicConfig(level=logging.DEBUG, format=config.LOG_FORMAT)

    inst = tornado.ioloop.IOLoop.instance()
    application = Application()
    app = tornado.httpserver.HTTPServer(application)
    app.listen(8888)

    rsa_setup()

    new_transactions = NewTransactionHandler(
        application.db,
        q_after=queues['auth_destination'])

    auth_destination = AuthDestinationHandler(
        application.db,
        q_init=queues['auth_destination'],
        q_void=queues['void'],
        q_after=queues['auth_source'])

    auth_source = AuthSourceHandler(
        application.db,
        q_init=queues['auth_source'],
        q_void=queues['void'],
        q_after=queues['capture_source'])

    capture_source = CaptureSourceHandler(
        application.db,
        q_init=queues['capture_source'],
        q_void=queues['void'],
        q_after=queues['capture_destination'])

    capture_destination = CaptureDestinationHandler(
        application.db,
        q_init=queues['capture_destination'],
        q_void=queues['void'])

    inst.add_callback(new_transactions.main_processing)
    inst.add_callback(auth_source.main_processing)
    inst.add_callback(auth_destination.main_processing)
    inst.add_callback(capture_source.main_processing)
    inst.add_callback(capture_destination.main_processing)

    inst.start()


if __name__ == "__main__":
    main()
