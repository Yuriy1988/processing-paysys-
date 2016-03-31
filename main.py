import logging
import tornado.ioloop
from tornado.queues import PriorityQueue
import tornado.web
import tornado.httpserver
import momoko

import config
from payment_api.handler import MainHandler
from processing.processing_daemon import AuthSourceHandler, AuthDestinationHandler, CaptureSourceHandler, CaptureDestinationHandler, \
    NewTransactionHandler

queues = {'auth_source': PriorityQueue(),
          'auth_destignation': PriorityQueue(),
          'capture_source': PriorityQueue(),
          'capture_destignation': PriorityQueue(),
          'void': PriorityQueue()
          }




class Application(tornado.web.Application):
    """ Tornado server application. """

    def __init__(self):

        """ Configure handlers and settings. """
        handlers = [
        (r"/", MainHandler, dict(q=queues['auth_source'])),
        ]

        settings = dict(
            debug=True,
        )
        self.db = momoko.Pool(
            dsn='dbname={dbname} user={username} password={password} host={host} port={port}'.format(dbname=config.DB_NAME,
                                                                                                     username=config.DB_USER,
                                                                                                     password=config.DB_USER_PASSWORD,
                                                                                                     host=config.DB_HOST,
                                                                                                     port=config.DB_PORT),
            # size=1,
        )
        self.db.connect()

        super(Application, self).__init__(handlers, **settings)




def main():
    logging.basicConfig(level=logging.DEBUG, format=config.LOG_FORMAT)

    inst = tornado.ioloop.IOLoop.instance()
    application = Application()
    app = tornado.httpserver.HTTPServer(application)
    app.listen(8888)
    new_transactions = NewTransactionHandler(application.db,
                                             q_after=queues['auth_destignation'])
    auth_destination = AuthDestinationHandler(application.db, q_init=queues['auth_destignation'],
                                                              q_void=queues['void'],
                                                              q_after=queues['auth_source'])
    auth_source = AuthSourceHandler(application.db, q_init=queues['auth_source'],
                                                    q_void=queues['void'],
                                                    q_after=queues['capture_source'])

    capture_source = CaptureSourceHandler(application.db, q_init=queues['capture_source'],
                                                          q_void=queues['void'],
                                                          q_after=queues['capture_destignation'])
    capture_destination = CaptureDestinationHandler(application.db,
                                                    q_init=queues['capture_destignation'],
                                                    q_void=queues['void'])
    inst.add_callback(new_transactions.main_processing)
    inst.add_callback(auth_source.main_processing)
    inst.add_callback(auth_destination.main_processing)
    inst.add_callback(capture_source.main_processing)
    inst.add_callback(capture_destination.main_processing)
    inst.start()


if __name__ == "__main__":
    main()