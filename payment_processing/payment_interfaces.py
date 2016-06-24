from importlib import reload

from . import store_interfaces
from .processing import ProcessingException


def process(pi_name, method_name, transaction):
    m = __import__(".".join([__name__, pi_name]), fromlist=[method_name])
    reload(m)
    pi_class = BasePI.__subclasses__()[0]
    if hasattr(pi_class, method_name):
        return getattr(pi_class, method_name)(transaction)
    else:
        raise ProcessingException("METHOD NOT FOUND")


class BasePI:

    @staticmethod
    def auth_destination(transaction):
        return transaction

    @staticmethod
    def auth_source(transaction):
        if not store_interfaces.check(transaction):
            raise ProcessingException("Store checking failed.")
        return transaction

    @staticmethod
    def capture_destination(transaction):
        return transaction

    @staticmethod
    def capture_source(transaction):
        store_interfaces.withdraw(transaction)
        return transaction

    @staticmethod
    def void(transaction):
        return transaction
