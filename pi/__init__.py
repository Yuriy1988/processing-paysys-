from pi.base import BasePI
from importlib import reload


class ProcessingException(Exception):
    pass


def process(pi_name, method_name, transaction):
    m = __import__(".".join([__name__, pi_name]), fromlist=[method_name])
    reload(m)
    pi_class = BasePI.__subclasses__()[0]
    if hasattr(pi_class, method_name):
        return getattr(pi_class, method_name)(transaction)
    else:
        raise ProcessingException("METHOD NOT FOUND")
