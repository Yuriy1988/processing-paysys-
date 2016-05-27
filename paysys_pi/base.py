import json

import crypt
import store_api
from config import config


def decode_transaction(func):
    def decoder(transaction):
        crypted = transaction["source"]["payment_requisites"]["crypted_payment"]
        transaction["source"]["payment_requisites"].update(
            json.loads(crypt.decrypt(crypted, config.RSA_KEY)) + {"crypted_payment": crypted}
        )
        result = func(transaction)
        result["source"]["payment_requisites"] = {"crypted_payment": crypted}
        return result

    return decoder


class ProcessingException(Exception):
    pass


class BasePI:

    @staticmethod
    def auth_destination(transaction):
        return transaction

    @staticmethod
    def auth_source(transaction):
        if not store_api.check(transaction):
            raise ProcessingException("Store checking failed.")
        return transaction

    @staticmethod
    def capture_destination(transaction):
        return transaction

    @staticmethod
    def capture_source(transaction):
        store_api.withdraw(transaction)
        return transaction

    @staticmethod
    def void(transaction):
        return transaction
