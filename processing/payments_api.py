from random import random, randint, choice
from tornado import gen


class TestPaymentSystem():

    @gen.coroutine
    def auth(self, data):
        time = randint(1, 10)
        yield gen.sleep(time)

        return {'status': choice(['ok', 'wait', 'decline']), 'time': time}

    @gen.coroutine
    def capture(self, data):
        time = randint(1, 10)
        yield gen.sleep(time)

        return time