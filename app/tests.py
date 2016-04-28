import motor
import tornado.ioloop
import tornado.testing
import unittest
from unittest.mock import MagicMock

import config_loader

# changing configs before importing Processing

from pi import ProcessingException
from app.processing import Processing
from app.rabbitmq_connector import RabbitPublisher, RabbitAsyncConsumer


config = config_loader.config
config.load_from_file("config", "Testing")


class ProcessingTests(unittest.TestCase):

    def setUp(self):
        self.transaction = None

    def tearDown(self):
        self.transaction = None

    def _correct_pi_factory(self, status):
        def payment_method(transaction):
            pi_name = transaction["source"]["paysys_contract"]["payment_interface"]
            self.transaction = getattr(TestPaymentInterface, status.lower())(transaction)
            return self.transaction
        return payment_method

    def _failure_pi_factory(self, status):
        def payment_method(transaction):
            pi_name = transaction["source"]["paysys_contract"]["payment_interface"]
            self.transaction = getattr(TestPaymentInterfaceWithFail, status.lower())(transaction)
            return self.transaction
        return payment_method

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
            processing.stop()
            io_loop.stop()
        io_loop.add_callback(callback, result)
        io_loop.start()
        return result.message

    def test_ok(self):
        self.transaction = {"id": "876", "source": {"paysys_contract": {"payment_interface": "test_pi"}}}
        expected_status = "OK"
        actual_result = self.processing_cycle(self.transaction)
        self.assertEqual(actual_result.get("status"), expected_status)

    def test_status_order(self):
        Processing._pi_factory = MagicMock(side_effect=self._correct_pi_factory)
        self.transaction = {"id": "876", "source": {"paysys_contract": {"payment_interface": "test_pi"}}}
        expected_order = ['AUTH SOURCE', 'AUTH DESTINATION', 'CAPTURE SOURCE', 'CAPTURE DESTINATION']
        self.processing_cycle(self.transaction)
        self.assertListEqual(expected_order, self.transaction.get("history"))

    def test_pi_failure(self):
        Processing._pi_factory = MagicMock(side_effect=self._failure_pi_factory)
        self.transaction = {"id": "876", "source": {"paysys_contract": {"payment_interface": "test_pi"}}}
        expected_order = ['AUTH SOURCE', 'AUTH DESTINATION', 'CAPTURE SOURCE', 'CAPTURE DESTINATION', 'VOID']
        self.processing_cycle(self.transaction)
        self.assertListEqual(expected_order, self.transaction.get("history"))

    def test_incorrect_transaction(self):
        self.transactio = {"id": "876", "source": {"paysys_contract": {}}}
        expected_status = "FAIL"
        actual_result = self.processing_cycle(self.transactio)
        self.assertEqual(actual_result.get("status"), expected_status)

    def test_transaction_exists(self):
        db = getattr(motor.MotorClient(), config.DB_NAME)
        db.transactions.insert({"_id": "876"})
        self.transactio = {"id": "876"}
        expected_status = "FAIL"
        actual_result = self.processing_cycle(self.transactio)
        self.assertEqual(actual_result.get("status"), expected_status)


class TestPaymentInterface:
    @staticmethod
    def save_history(transaction, name):
        if "history" in transaction:
            transaction["history"].append(name)
        else:
            transaction["history"] = [name]
        return transaction

    @staticmethod
    def auth_destination(transaction):
        transaction = TestPaymentInterface.save_history(transaction, "AUTH DESTINATION")
        return transaction

    @staticmethod
    def auth_source(transaction):
        transaction = TestPaymentInterface.save_history(transaction, "AUTH SOURCE")
        return transaction

    @staticmethod
    def capture_destination(transaction):
        transaction = TestPaymentInterface.save_history(transaction, "CAPTURE DESTINATION")
        return transaction

    @staticmethod
    def capture_source(transaction):
        transaction = TestPaymentInterface.save_history(transaction, "CAPTURE SOURCE")
        return transaction

    @staticmethod
    def void(transaction):
        transaction = TestPaymentInterface.save_history(transaction, "VOID")
        return transaction


class TestPaymentInterfaceWithFail(TestPaymentInterface):

    @staticmethod
    def capture_destination(transaction):
        transaction = TestPaymentInterface.save_history(transaction, "CAPTURE DESTINATION")
        raise ProcessingException("")
