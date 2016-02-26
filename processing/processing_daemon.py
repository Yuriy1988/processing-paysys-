import datetime
import json
from random import randint
import traceback
from tornado import gen, httpclient
from tornado.queues import Queue, QueueEmpty
from processing.payments_api import TestPaymentSystem


class ProcessingAbstractHandler():

    def __init__(self, db, q_init=None, q_after=None):
        self.db = db
        self.q_init = q_init
        self.q_after = q_after
        self.http_client = httpclient.HTTPClient()
        self.paym_syst = TestPaymentSystem()


    @gen.coroutine
    def main_processing(self):
        while True:
            try:
                q_data = yield self.q_init.get()
                q_data = json.loads(q_data)
                result = yield self.handle_data(q_data)
                result = json.dumps(result)
                yield self.q_after.put(result)
            except Exception as e:
                print(traceback.format_exc())

    @gen.coroutine
    def handle_data(self, q_data):
        pass

    def get_payment_method(self, data):
        pass


class AuthSourceHandler(ProcessingAbstractHandler):


    @gen.coroutine
    def handle_data(self, q_data):
        if q_data['type'] == 'paypal':
            result = yield self.paym_syst.auth(1)
            print('1 %s %s' % (q_data['transaction_id'], result))

        cursor = self.db.db_update_status(q_data['transaction_id'], 'auth_so')
        return q_data


class AuthDestinationHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def handle_data(self, q_data):
        if q_data['type'] == 'paypal':

            result = yield self.paym_syst.auth(1)
            print('2 %s %s' % (q_data['transaction_id'], result))
        cursor = self.db.db_update_status(q_data['transaction_id'], 'auth_de')
        return q_data


class CaptureSourceHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def handle_data(self, q_data):
        if q_data['type'] == 'paypal':
            result=yield self.paym_syst.auth(1)
            print('3 %s %s' % (q_data['transaction_id'], result))
        cursor = self.db.db_update_status(q_data['transaction_id'], 'capc_so')
        return q_data


class CaptureDestinationHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def handle_data(self, q_data):
        if q_data['type'] == 'paypal':
            result = yield self.paym_syst.auth(1)
            print('4 %s %s' % (q_data['transaction_id'], result))
        cursor = self.db.db_update_status(q_data['transaction_id'], 'approved')
        return q_data


