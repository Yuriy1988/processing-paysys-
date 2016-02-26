from decimal import Decimal
from random import random, randint
import traceback
from tornado import gen
import tornado.web
import json


import settings


CURRENCY_LIST = ['EUR', 'USD', 'UAH', 'RUR']


def visa_master_serializer(data=None):
    if not data:
        raise ValueError
    return data


def paypal_serializer(data=None):
    if not data:
        raise ValueError
    return data


def bitcoin_serializer(data=None):
    if not data:
        raise ValueError
    return data

transaction_source_serializers = {
    'visa_master': visa_master_serializer,
    'paypal': paypal_serializer,
    'bitcoin': bitcoin_serializer
}


class DBConnection():

    def __init__(self, db):
        self.db = db

    @gen.coroutine
    def db_execute(self, sql, insert_data):
        cursor = yield self.db.execute(sql, insert_data)
        cursor_id = cursor.fetchone()
        cursor.close()
        return cursor_id[0]

    @gen.coroutine
    def db_update_status(self, id, status):
        cursor = yield self.db.execute('UPDATE transactions SET status=%s WHERE id=%s;', (status, id))
        return cursor

    @gen.coroutine
    def db_select_status(self, id):
        cursor = yield self.db.execute('SELECT status FROM transactions WHERE id=%s;', (id,))
        return cursor.fetchone()[0]


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db


class MainHandler(BaseHandler):

    def initialize(self, q=None):
        self.q = q

    @gen.coroutine
    def get(self):
        try:
            id = int(self.request.arguments.get('id')[0])
            transaction_status = yield self.db.db_select_status(id)
            self.write({'transaction_status': transaction_status})
            self.finish()
        except Exception as e:
            print(traceback.format_exc())

    @gen.coroutine
    def post(self):
        try:
            transaction_data = request_serialazer(self.request.body.decode("utf-8"))
            # transaction_data['source'] = encrypt(settings.PASSWORD, transaction_data['source'])
            # transaction_data['destination'] = encrypt(settings.PASSWORD, transaction_data['destination'])
            transaction_data['status'] = 'initiate'
            queue_data = transaction_data.copy()
            transaction_data.pop("type", None)
            transaction_data["id"] = randint(10000, 1000000)
            transaction_id = yield self.db.db_execute("""INSERT INTO transactions (id, status, source, currency, destination)
                                          VALUES (%(id)s, %(status)s, %(source)s, %(currency)s, %(destination)s) RETURNING ID;""",
                                                 transaction_data)
            queue_data['transaction_id'] = transaction_id
            self.q.put_nowait(json.dumps(queue_data))
            self.write({'transaction_id': transaction_id})
            self.finish()
        except ValueError:
            print(traceback.format_exc())


def request_serialazer(request):
    data = json.loads(request)
    transaction_type = data.get('type')
    transaction_source_serializer = transaction_source_serializers.get(transaction_type)
    transaction_currency = data.get('currency')
    transaction_amount = data.get('amount')
    if not transaction_source_serializer or not transaction_currency or not transaction_amount \
            or transaction_currency not in CURRENCY_LIST:
        raise ValueError
    transaction_amount = int(transaction_amount)
    transaction_source = transaction_source_serializer(data.get('source'))
    transaction_destination = destination_serializer(data.get('destination'))
    return {'type': transaction_type,
            'source': json.dumps(transaction_source),
            'destination': json.dumps(transaction_destination),
            'amount': transaction_amount,
            'currency': transaction_currency}


def destination_serializer(destination_data):
    if not destination_data:
        raise ValueError
    return destination_data




