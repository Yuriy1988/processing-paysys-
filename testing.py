#!venv/bin/python
import os
import unittest
import asyncio
import asynctest.case
from copy import deepcopy

from app import create_app, shutdown_tasks
from payment_processing import Processing

__author__ = 'Kostel Serhii'


class ProcessingTestMock:

    _transaction = {
        "id":  "00000000-1111-2222-3333-444444444444",

        "payment": {
            "status": "ACCEPTED",
            "paysys_id": "PAY_PAL",
            "payment_account": "test",
            "description":  "Test payment",
            "invoice": {
                "order_id": "order_id_1",
                "store_id": "88888888-1111-2222-3333-444444444444",
                "total_price": "80.5",
                "currency": "USD",
                "items": [
                    {
                        "store_item_id": "store_item_id_1",
                        "quantity": 3,
                        "unit_price": "23.5"
                    },
                    {
                        "store_item_id": "store_item_id_2",
                        "quantity": 1,
                        "unit_price": "10"
                    }
                ]
            },
        },

        "source": {
            "paysys_contract": {
                "id":  1,
                "contractor_name":  "Test paysys contractor",
                "paysys_id": "VISA_MASTER",
                "commission_fixed":  "0",
                "commission_pct":  "1",
                "currency": "USD",
                "payment_interface": "privat"
            },
            "payment_requisites": {
                "crypted_payment":  "tnemyap_detpyrc"
            }
        },

        "destination": {
            "merchant_contract": {
                "id":  1,
                "merchant_id":  "99999999-1111-2222-3333-444444444444",
                "commission_fixed":  "0",
                "commission_pct":  "1",
                "currency": "USD"
            },
            "merchant_account": {
                "bank_name": "privat",
                "checking_account": "Test merchant checking account",
                "currency": "USD",
                "mfo": "123456",
                "okpo": "12345678"
            },
        },

        "store": {
            "id": "00000000-1111-2222-3333-444444444444",
            "store_name": "The Greatest Store Ever!",
            "store_url": "http://www.greatest.com",
            "store_identifier": "dss9-asdf-sasf-fsaa",
            "category": None,
            "description": "Desdafggagagagas",
            "logo": None,
            "show_logo": False,
            "merchant_id": "dss9-asdf-sasf-fsda",
            "store_settings":
            {
                "sign_algorithm": "sign_algorithm",
                "sign_key": "somethingdfsfdf",
                "succeed_url": "sdfasdfasfasfsdfasfsdf",
                "failure_url": "sdfasfasfasdfasdfasdfasd",
                "commission_pct": "10.0"
            }
        },
    }

    def __init__(self):
        self._queue_trans_status = asyncio.Queue()
        self._processing = None

    def register_test_processing(self, db):
        self._queue_trans_status = asyncio.Queue()
        self._processing = Processing(
            db=db,
            results_handler=self._queue_trans_status.put
        )
        return self._processing

    async def get_trans_status(self):
        result = await self._queue_trans_status.get()
        return result

    async def put_trans_for_processing(self, transaction):
        result = await self._processing.transaction_handler(transaction)
        return result

    async def put_3d_secure_result(self, message):
        result = await self._processing.response_3d_secure_handler(message)
        return result

    def get_transaction(self, trans_id=None, status="ACCEPTED", paysys_id="PAY_PAL", extra_info=None):
        trans = deepcopy(self._transaction)

        trans['id'] = trans_id or trans['id']
        trans['payment']['status'] = status
        trans['payment']['paysys_id'] = paysys_id

        if extra_info is not None:
            trans['extra_info'] = extra_info

        return trans


class BaseTestCase(asynctest.case.TestCase, ProcessingTestMock):

    def setUp(self):
        super().setUp()
        self.app = self.get_app(self.loop)
        self.db = self.app['db']

        # Create test processing connection
        self.app['processing'] = self.register_test_processing(self.db)

    async def tearDown(self):
        await self.db.transaction.drop()

        queue_listener = self.app['queue_listener']
        await queue_listener.clean()

        queue_publisher = self.app['queue_publisher']
        await queue_publisher.clean()

        await self.app.shutdown()
        await shutdown_tasks()

        super().tearDown()

    def get_app(self, loop):
        return create_app('test', loop=loop)


def run_tests():
    tests_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tests')
    suite = unittest.TestLoader().discover(tests_path, pattern='*.py')
    return unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    run_tests()
