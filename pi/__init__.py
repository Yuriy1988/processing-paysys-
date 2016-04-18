from pi.base import BasePI


def process(pi_name, method_name, transaction):
    __import__(".".join([__name__, pi_name]), fromlist=[method_name])
    pi_class = BasePI.__subclasses__()[0]
    if hasattr(pi_class, method_name):
        return getattr(pi_class, method_name)(transaction)
    else:
        raise Exception("METHOD NOT FOUND")
