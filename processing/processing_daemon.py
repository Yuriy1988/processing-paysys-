import datetime
import json
from random import randint
import traceback
from tornado import gen, httpclient
from tornado.queues import Queue, QueueEmpty
from processing.payments_api import TestPaymentSystem


class ProcessingAbstractHandler():

    def __init__(self, db, q_init=None, q_void=None, q_after=None):
        self.db = db
        self.q_init = q_init
        self.q_after = q_after
        self.q_void = q_void
        self.http_client = httpclient.HTTPClient()
        self.paym_syst = TestPaymentSystem()


    @gen.coroutine
    def main_processing(self):
        while True:
            try:
                q_data = yield self.q_init.get()
                q_data = json.loads(q_data)
                result = yield self.handle_data(q_data)

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
        elif q_data['type'] == 'credit_card':
            result = yield self.paym_syst.auth(1)
        if result and result['status'] == 'ok':
            print('AuthSource %s %s' % (q_data['transaction_id'], result['time']))
            cursor = self.db.db_update_status(q_data['transaction_id'], 'auth_so')
            yield self.q_after.put(json.dumps(q_data))
            return q_data
        elif result and result['status'] == 'wait':
            yield self.q_init.put(json.dumps(q_data))
            print('AuthSource wait %s %s' % (q_data['transaction_id'], result['time']))
            return q_data
        else:
            print('AuthSource decline %s %s' % (q_data['transaction_id'], result['time']))
            cursor = self.db.db_update_status(q_data['transaction_id'], 'decline')
            yield self.q_void.put(json.dumps(q_data))
            return q_data


class AuthDestinationHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def handle_data(self, q_data):
        if q_data['type'] == 'paypal':

            result = yield self.paym_syst.auth(1)
        elif q_data['type'] == 'credit_card':
            result = yield self.paym_syst.auth(1)
        if result and result['status'] == 'ok':
            print('AuthDestination %s %s' % (q_data['transaction_id'], result['time']))
            cursor = self.db.db_update_status(q_data['transaction_id'], 'auth_de')
            yield self.q_after.put(json.dumps(q_data))
            return q_data
        elif result and result['status'] == 'wait':
            yield self.q_init.put(json.dumps(q_data))
            print('AuthDestination wait %s %s' % (q_data['transaction_id'], result['time']))
            return q_data
        else:
            print('AuthDestination decline %s %s' % (q_data['transaction_id'], result['time']))
            cursor = self.db.db_update_status(q_data['transaction_id'], 'decline')
            yield self.q_void.put(json.dumps(q_data))
            return q_data


class CaptureSourceHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def handle_data(self, q_data):
        if q_data['type'] == 'paypal':
            result=yield self.paym_syst.auth(1)
        elif q_data['type'] == 'credit_card':
            result = yield self.paym_syst.auth(1)
        if result and result['status'] == 'ok':
            print('CaptureSource %s %s' % (q_data['transaction_id'], result['time']))
            cursor = self.db.db_update_status(q_data['transaction_id'], 'capc_so')
            yield self.q_after.put(json.dumps(q_data))
            return q_data
        elif result and result['status'] == 'wait':
            yield self.q_init.put(json.dumps(q_data))
            print('CaptureSource wait %s %s' % (q_data['transaction_id'], result['time']))
            return q_data
        else:
            print('CaptureSource decline %s %s' % (q_data['transaction_id'], result['time']))
            cursor = self.db.db_update_status(q_data['transaction_id'], 'decline')
            yield self.q_void.put(json.dumps(q_data))
            return q_data


class CaptureDestinationHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def handle_data(self, q_data):
        if q_data['type'] == 'paypal':
            result = yield self.paym_syst.auth(1)
        elif q_data['type'] == 'credit_card':
            result = yield self.paym_syst.auth(1)
        if result and result['status'] == 'ok':
            print('CaptureDestination %s %s' % (q_data['transaction_id'], result['time']))
            cursor = self.db.db_update_status(q_data['transaction_id'], 'approved')
            return q_data
        elif result and result['status'] == 'wait':
            yield self.q_init.put(json.dumps(q_data))
            print('CaptureDestination wait %s %s' % (q_data['transaction_id'], result['time']))
            return q_data
        else:
            print('CaptureDestination decline %s %s' % (q_data['transaction_id'], result['time']))
            cursor = self.db.db_update_status(q_data['transaction_id'], 'decline')
            yield self.q_void.put(json.dumps(q_data))
            return q_data


