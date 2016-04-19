import json

import config
import crypt


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


class BasePI:

    @staticmethod
    def auth_destination(transaction):
        return transaction

    @staticmethod
    def auth_source(transaction):
        return transaction

    @staticmethod
    def capture_destination(transaction):
        return transaction

    @staticmethod
    def capture_source(transaction):
        return transaction

    @staticmethod
    def void(transaction):
        return transaction
