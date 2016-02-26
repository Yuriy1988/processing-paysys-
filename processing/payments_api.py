from random import random, randint
from tornado import gen


class TestPaymentSystem():

    @gen.coroutine
    def auth(self, data):
        time = randint(1, 10)
        yield gen.sleep(time)

        return time

    @gen.coroutine
    def capture(self, data):
        time = randint(1, 10)
        yield gen.sleep(time)

        return time