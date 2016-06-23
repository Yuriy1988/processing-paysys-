import asyncio
import motor
import unittest
from unittest.mock import MagicMock

from config import config

# changing configs before importing Processing

from paysys_pi import ProcessingException
from processing.processing import Processing
from processing.rabbitmq_connector import RabbitPublisher, RabbitAsyncConsumer


config.load_from_file("config", "Testing")


class ProcessingTests(unittest.TestCase):
    _transaction = {
        "id": "876",
        "store_api": "test_api",
        "source": {"paysys_contract": {"payment_interface": "test_pi"}}
    }

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
        loop = asyncio.get_event_loop()

        db = getattr(motor.MotorClient(), config.DB_NAME)
        processing = Processing(db=db, loop=loop)
        processing.init()

        rabbit_sender = RabbitPublisher(queue_name=config.INCOME_QUEUE_NAME)
        rabbit_receiver = RabbitAsyncConsumer(queue_name=config.OUTCOME_QUEUE_NAME)

        rabbit_sender.put(transaction)

        result = None
        async def callback():
            global result
            result = await rabbit_receiver.get()
            rabbit_receiver.close_connection()
            await db.transactions.remove({"_id": transaction["id"]})
            processing.stop()

        loop.run_until_complete(callback())
        return result

    def test_ok(self):
        self.transaction = self._transaction
        expected_status = "OK"
        actual_result = self.processing_cycle(self.transaction)
        self.assertEqual(expected_status, actual_result.get("status"))

    def test_status_order(self):
        Processing._pi_factory = MagicMock(side_effect=self._correct_pi_factory)
        self.transaction = self._transaction
        expected_order = ['AUTH SOURCE', 'AUTH DESTINATION', 'CAPTURE SOURCE', 'CAPTURE DESTINATION']
        self.processing_cycle(self.transaction)
        self.assertListEqual(expected_order, self.transaction.get("history"))

    def test_pi_failure(self):
        Processing._pi_factory = MagicMock(side_effect=self._failure_pi_factory)
        self.transaction = self._transaction
        expected_order = ['AUTH SOURCE', 'AUTH DESTINATION', 'CAPTURE SOURCE', 'CAPTURE DESTINATION', 'VOID']
        self.processing_cycle(self.transaction)
        self.assertListEqual(expected_order, self.transaction.get("history"))

    def test_incorrect_transaction(self):
        self.transactio = {"id": "876", "source": {"paysys_contract": {}}}
        expected_status = "FAIL"
        actual_result = self.processing_cycle(self.transactio)
        self.assertEqual(expected_status, actual_result.get("status"))

    def test_transaction_exists(self):
        db = getattr(motor.MotorClient(), config.DB_NAME)
        db.transactions.insert({"_id": "876"})
        self.transactio = {"id": "876"}
        expected_status = "FAIL"
        actual_result = self.processing_cycle(self.transactio)
        self.assertEqual(expected_status, actual_result.get("status"))


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
