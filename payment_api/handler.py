import traceback
from tornado import gen
import tornado.web

import config
from rabbitmq_connector import PublishingClient

class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db


class MainHandler(BaseHandler):

    def initialize(self, q=None):
        self.q = q

    @gen.coroutine
    def post(self):
        try:
            print(self.request.body.decode("utf-8"))
            self.rabbitmq_publisher = PublishingClient(config.RABBITMQ_URL ,'xopay_processing')
            yield self.rabbitmq_publisher.connect()
            yield self.rabbitmq_publisher.publish(self.request.body.decode("utf-8"))
            self.finish()
        except ValueError:
            print(traceback.format_exc())






