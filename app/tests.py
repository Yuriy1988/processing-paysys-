from datetime import timedelta

import motor
import tornado.ioloop
import unittest
import config

config.RABBIT_HOST = '127.0.0.1'
config.RABBIT_PORT = 5672
config.INCOME_QUEUE_NAME = 'test_transactions_for_processing'
config.OUTCOME_QUEUE_NAME = 'test_statuses'
config.DB_NAME = "test_processing_db"

from app.processing import Processing
from app.rabbitmq_connector import RabbitPublisher, RabbitAsyncConsumer


class ProcessingTests(unittest.TestCase):

    @staticmethod
    def processing_cycle(transaction):
        io_loop = tornado.ioloop.IOLoop.current()

        db = getattr(motor.MotorClient(), config.DB_NAME)
        processing = Processing(db=db)
        processing.init(ioloop=io_loop)

        rabbit_sender = RabbitPublisher(queue_name=config.INCOME_QUEUE_NAME)
        rabbit_receiver = RabbitAsyncConsumer(io_loop, queue_name=config.OUTCOME_QUEUE_NAME)

        rabbit_sender.put(transaction)

        class Result:
            pass
        result = Result()
        async def callback(r):
            r.message = await rabbit_receiver.get()
            rabbit_receiver.close_connection()
            await db.transactions.remove({"_id": transaction["id"]})
            io_loop.stop()
        io_loop.add_callback(callback, result)

        io_loop.start()
        return result.message

    def test_ok(self):
        transaction = {"id": "876", "source": {"paysys_contract": {"payment_interface": "test_pi"}}}
        expected_status = "OK"
        actual_result = self.processing_cycle(transaction)
        self.assertEqual(actual_result.get("status"), expected_status)

    def test_incorrect_transaction(self):
        transaction = {"id": "876", "source": {"paysys_contract": {}}}
        expected_status = "FAIL"
        actual_result = self.processing_cycle(transaction)
        self.assertEqual(actual_result.get("status"), expected_status)

    def test_transaction_exists(self):
        db = getattr(motor.MotorClient(), config.DB_NAME)
        db.transactions.insert({"_id": "876"})
        transaction = {"id": "876"}
        expected_status = "FAIL"
        actual_result = self.processing_cycle(transaction)
        self.assertEqual(actual_result.get("status"), expected_status)
