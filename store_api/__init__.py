import logging

from importlib import reload
from store_api.base import BaseAPI


def check(transaction):
    return _find_api("check", transaction)


def withdraw(transaction):
    return _find_api("withdraw", transaction)


def _find_api(func_name, transaction):
    m = __import__(".".join([__name__, transaction.get("store_api")]), fromlist=[func_name])
    reload(m)
    pi_class = BaseAPI.__subclasses__()[0]
    if hasattr(pi_class, func_name):
        return getattr(pi_class, func_name)(transaction)
    else:
        logging.error("Fail to find store API")
