import json
import logging
import traceback
from tornado import gen, httpclient

import config
from processing import crypt
from processing.payments_api import TestPaymentSystem
from processing.serializers import request_serialazer
from db_connector import DBConnection
from rabbitmq_connector import ConsumingClient, PublishingClient


log = logging.getLogger(__name__)


class ProcessingAbstractHandler:

    def __init__(self, db, q_init=None, q_void=None, q_after=None):
        self.db = DBConnection(db)
        self.q_init = q_init
        self.q_after = q_after
        self.q_void = q_void
        self.http_client = httpclient.HTTPClient()
        self.rabbitmq_publisher = PublishingClient(config.RABBITMQ_URL ,config.TRANSACTION_STATUS_QUEUE)

    @gen.coroutine
    def main_processing(self):
        yield self.rabbitmq_publisher.connect()
        while True:
            try:
                q_data = yield self.q_init.get()
                q_data = json.loads(q_data)
                result = yield self.handle_data(q_data)
            except Exception as e:
                log.error(traceback.format_exc())

    @gen.coroutine
    def handle_data(self, q_data):
        pass

    def get_payment_method(self, data):
        # TODO: make normal system
        dict_of_paym_systems = {
            0: TestPaymentSystem()
        }
        if data['type'] == 'credit_card':
            paym_system_id = data['source_merchant_data']['paysys_id']
            paym_system = dict_of_paym_systems.get(paym_system_id)
            if not paym_system:
                pass
            return paym_system
        pass


class NewTransactionHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def main_processing(self):
        self.rabbitmq_consumer = ConsumingClient(config.RABBITMQ_URL, config.NEW_TRANSACTIONS_QUEUE)
        try:
            yield self.rabbitmq_consumer.connect()
            while True:
                try:
                    new_task = yield self.rabbitmq_consumer.get_message()
                    log.info(new_task)
                    yield self.handle_data(new_task)
                except Exception as e:
                    log.error(traceback.format_exc())
        except Exception as e:
            log.error(traceback.format_exc())

    @gen.coroutine
    def handle_data(self, q_data):
        print(q_data)
        transaction_data = request_serialazer(q_data.decode("utf-8"))
        transaction_data['status'] = 'initiate'
        data_to_base = transaction_data.copy()
        data_to_base['source_merchant_data'] = json.dumps(data_to_base['source_merchant_data'])
        data_to_base['source'] = crypt.encrypt(json.dumps(data_to_base['source']), config.SECRET_KEY)
        data_to_base['destination'] = json.dumps(data_to_base['destination'])
        transaction_id = yield self.db.db_insert_transacton(data_to_base)
        transaction_data['transaction_id'] = transaction_id

        yield self.q_after.put(json.dumps(transaction_data))
        print({'transaction_id': transaction_id})


class AuthSourceHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def handle_data(self, q_data):
        paym_system = self.get_payment_method(q_data)
        if q_data.get('waiting_order'):
            result = yield paym_system.order_status(q_data['waiting_order'])
        else:
            result = yield paym_system.auth(q_data['source']['cardnumber'],
                                            q_data['source']['cvv'],
                                            q_data['source']['expdate'],
                                            q_data['source_merchant_data']['merid'],
                                            q_data['amount'],
                                            q_data['currency'],
                                            q_data['description'])
        if result and result['status'] == 'ok':
            log.info('AuthSource transactionid %s ok' % (q_data['transaction_id']))
            yield self.db.db_update_status(q_data['transaction_id'], 'auth_source')
            yield self.db.db_add_auth_response(q_data['transaction_id'], result['response'], result['order_id'])
            if q_data.get('waiting_order'):
                q_data.pop('waiting_order')
            q_data['hold_id'] = result['order_id']
            yield self.q_after.put(json.dumps(q_data))
            return q_data
        elif result and result['status'] == 'wait':
            yield self.q_init.put(json.dumps(q_data))
            if result.get('order_id'):
                q_data['waiting_order'] = result['order_id']  # if we have order_id of transaction but dont have final response
                yield self.db.db_add_auth_response(q_data['transaction_id'], result['response'], result['order_id'])
            log.info('AuthSource wait %s' % (q_data['transaction_id']))
            return q_data
        elif result and result['status'] == '3ds':
            log.info('AuthSource need 3ds %s' % (q_data['transaction_id']))
            yield self.db.db_update_status(q_data['transaction_id'], 'auth_3ds')
            yield self.db.db_add_auth_response(q_data['transaction_id'], result['response'], result['order_id'])
            outer_queue_data = {'status': 'need_3ds', 'uuid': q_data['uuid'], 'url': result['url']}
            # yield self.rabbitmq_publisher.connect()
            yield self.rabbitmq_publisher.publish(json.dumps(outer_queue_data))
            # self.rabbitmq_publisher.close_connection()
            return q_data

        else:
            log.info('AuthSource decline %s' % (q_data['transaction_id']))
            yield self.db.db_update_status(q_data['transaction_id'], 'decline')
            yield self.db.db_add_auth_response(q_data['transaction_id'], result['response'], result['order_id'])
            yield self.q_void.put(json.dumps(q_data))
            outer_queue_data = {'status': 'decline', 'uuid': q_data['uuid']}
            # yield self.rabbitmq_publisher.connect()
            yield self.rabbitmq_publisher.publish(json.dumps(outer_queue_data))
            # self.rabbitmq_publisher.close_connection()
            return q_data


class AuthDestinationHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def handle_data(self, q_data):
        # TODO: make auth destination method
        result = {'status': 'ok'}
        if result and result['status'] == 'ok':
            log.info('AuthDestination %s' % (q_data['transaction_id']))
            yield self.db.db_update_status(q_data['transaction_id'], 'auth_destination')
            yield self.q_after.put(json.dumps(q_data))
            return q_data
        elif result and result['status'] == 'wait':
            yield self.q_init.put(json.dumps(q_data))
            log.info('AuthDestination wait %s' % (q_data['transaction_id']))
            return q_data
        else:
            log.info('AuthDestination decline %s' % (q_data['transaction_id']))
            yield self.db.db_update_status(q_data['transaction_id'], 'decline')
            yield self.q_void.put(json.dumps(q_data))
            outer_queue_data = {'status': 'decline', 'uuid': q_data['uuid']}
            # yield self.rabbitmq_publisher.connect()
            yield self.rabbitmq_publisher.publish(json.dumps(outer_queue_data))
            # self.rabbitmq_publisher.close_connection()
            return q_data


class CaptureSourceHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def handle_data(self, q_data):
        paym_system = self.get_payment_method(q_data)
        if q_data.get('waiting_order'):
            result = yield paym_system.order_status(q_data['waiting_order'])
        else:
            result = yield paym_system.capture(q_data['source']['cardnumber'],
                                                q_data['source']['cvv'],
                                                q_data['source']['expdate'],
                                                q_data['source_merchant_data']['merid'],
                                                q_data['amount'],
                                                q_data['currency'],
                                                q_data['description'],
                                                q_data['hold_id'])
        if result and result['status'] == 'ok':
            log.info('captureSource transaction id %s ok' % (q_data['transaction_id']))
            yield self.db.db_update_status(q_data['transaction_id'], 'capture_source')
            yield self.db.db_add_capture_response(q_data['transaction_id'], result['response'], result['order_id'])
            if q_data.get('waiting_order'):
                q_data.pop('waiting_order')
            yield self.q_after.put(json.dumps(q_data))
            return q_data
        elif result and result['status'] == 'wait':
            yield self.q_init.put(json.dumps(q_data))
            if result.get('order_id'):
                q_data['waiting_order'] = result['order_id']  # if we have order_id of transaction but dont have final response
                yield self.db.db_add_capture_response(q_data['transaction_id'], result['response'], result['order_id'])
            log.info('captureSource wait %s' % (q_data['transaction_id']))
            return q_data
        elif result and result['status'] == '3ds':
            log.info('captureSource need 3ds %s' % (q_data['transaction_id']))
            yield self.db.db_update_status(q_data['transaction_id'], 'capture_3ds')
            yield self.db.db_add_capture_response(q_data['transaction_id'], result['response'], result['order_id'])
            outer_queue_data = {'status': 'need_3ds', 'uuid': q_data['uuid'], 'url': result['url']}
            # yield self.rabbitmq_publisher.connect()
            yield self.rabbitmq_publisher.publish(json.dumps(outer_queue_data))
            # self.rabbitmq_publisher.close_connection()
            return q_data

        else:
            log.info('captureSource decline %s' % (q_data['transaction_id']))
            yield self.db.db_update_status(q_data['transaction_id'], 'decline')
            yield self.db.db_add_capture_response(q_data['transaction_id'], result['response'], result['order_id'])
            yield self.q_void.put(json.dumps(q_data))
            outer_queue_data = {'status': 'decline', 'uuid': q_data['uuid']}

            yield self.rabbitmq_publisher.publish(json.dumps(outer_queue_data))
            # self.rabbitmq_publisher.close_connection()
            return q_data


class CaptureDestinationHandler(ProcessingAbstractHandler):

    @gen.coroutine
    def handle_data(self, q_data):
        # TODO: make capture destination method
        result = {'status': 'ok'}
        if result and result['status'] == 'ok':
            log.info('CaptureDestination %s' % (q_data['transaction_id']))
            yield self.db.db_update_status(q_data['transaction_id'], 'approved')
            outer_queue_data = {'status': 'approved', 'uuid': q_data['uuid']}
            # yield self.rabbitmq_publisher.connect()
            yield self.rabbitmq_publisher.publish(json.dumps(outer_queue_data))
            # self.rabbitmq_publisher.close_connection()
            return q_data
        elif result and result['status'] == 'wait':
            yield self.q_init.put(json.dumps(q_data))
            log.info('CaptureDestination wait %s' % (q_data['transaction_id']))
            return q_data
        else:
            log.info('CaptureDestination decline %s' % (q_data['transaction_id']))
            yield self.db.db_update_status(q_data['transaction_id'], 'decline')
            yield self.q_void.put(json.dumps(q_data))
            outer_queue_data = {'status': 'decline', 'uuid': q_data['uuid']}
            # yield self.rabbitmq_publisher.connect()
            yield self.rabbitmq_publisher.publish(json.dumps(outer_queue_data))
            # self.rabbitmq_publisher.close_connection()
            return q_data
