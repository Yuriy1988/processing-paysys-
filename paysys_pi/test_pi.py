import time
import json

from paysys_pi import BasePI

DELAY_SEC = 0


class TestPI(BasePI):

    @staticmethod
    def auth_destination(transaction):
        time.sleep(DELAY_SEC)
        print('AUTH DST:    ', json.dumps(transaction))
        return transaction

    @staticmethod
    def auth_source(transaction):
        transaction = BasePI.auth_source(transaction)
        time.sleep(DELAY_SEC)
        print('AUTH SRC:    ', json.dumps(transaction))
        return transaction

    @staticmethod
    def capture_destination(transaction):
        time.sleep(DELAY_SEC)
        print('CAPTURE DST: ', json.dumps(transaction))
        return transaction

    @staticmethod
    def capture_source(transaction):
        time.sleep(DELAY_SEC)
        print('CAPTURE SRC: ', json.dumps(transaction))
        return transaction

    @staticmethod
    def void(transaction):
        time.sleep(DELAY_SEC)
        print('VOID: ', json.dumps(transaction))
        return transaction
