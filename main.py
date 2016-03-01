import tornado.ioloop
from tornado.queues import PriorityQueue
import tornado.web
import tornado.httpserver
import momoko

import settings
from payment_api.handler import MainHandler, DBConnection
from processing.processing_daemon import AuthSourceHandler, AuthDestinationHandler, CaptureSourceHandler, CaptureDestinationHandler

queues = {'auth_source': PriorityQueue(),
          'auth_destignation': PriorityQueue(),
          'capture_source': PriorityQueue(),
          'capture_destignation': PriorityQueue(),
          'void': PriorityQueue()
          }

handlers = [
        (r"/", MainHandler, dict(q=queues['auth_source'])),
    ]

settings_handler = dict(
    template_path='',
)




if __name__ == "__main__":
    inst = tornado.ioloop.IOLoop.instance()
    application = tornado.web.Application(handlers, **settings_handler)
    db_connection = momoko.Pool(
            dsn='dbname={dbname} user={username} password={password} host={host} port={port}'.format(dbname=settings.DB_NAME,
                                                                                                     username=settings.DB_USER,
                                                                                                     password=settings.DB_USER_PASSWORD,
                                                                                                     host=settings.DB_HOST,
                                                                                                     port=settings.DB_PORT),
            size=1,
            ioloop=inst,
        )
    db = DBConnection(db_connection)
    application.db = db
    app = tornado.httpserver.HTTPServer(application)
    app.listen(8888)
    auth_source = AuthSourceHandler(db, queues['auth_source'], queues['void'], queues['auth_destignation'])
    auth_destination = AuthDestinationHandler(db, queues['auth_destignation'], queues['void'], queues['capture_source'])
    capture_source = CaptureSourceHandler(db, queues['capture_source'], queues['void'], queues['capture_destignation'])
    capture_destination = CaptureDestinationHandler(db, queues['capture_destignation'], queues['void'])
    future = db_connection.connect()
    inst.add_future(future, lambda f: inst.stop())
    inst.add_callback(auth_source.main_processing)
    inst.add_callback(auth_destination.main_processing)
    inst.add_callback(capture_source.main_processing)
    inst.add_callback(capture_destination.main_processing)
    inst.start()
    future.result()
    inst.start()