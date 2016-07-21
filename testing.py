#!venv/bin/python
import os
import unittest
import asynctest.case

from app import create_app, shutdown_tasks

__author__ = 'Kostel Serhii'


class BaseTestCase(asynctest.case.TestCase):

    def get_app(self, loop):
        return create_app('test', loop=loop)

    def setUp(self):
        super().setUp()
        self.app = self.get_app(self.loop)

    async def tearDown(self):
        db = self.app['db']
        await db.transaction.drop()

        queue_listener = self.app['queue_listener']
        await queue_listener.clean()

        queue_publisher = self.app['queue_publisher']
        await queue_publisher.clean()

        await self.app.shutdown()
        await shutdown_tasks()

        super().tearDown()


def run_tests():
    tests_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tests')
    suite = unittest.TestLoader().discover(tests_path, pattern='*.py')
    return unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    run_tests()
