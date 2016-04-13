
RSA_KEY = None

CURRENCY_LIST = ['EUR', 'USD', 'UAH', 'RUR']

DB_USER = "xopayadmin"
DB_USER_PASSWORD = "xopay"
DB_NAME = "xopayprocessing"
DB_HOST = "localhost"
DB_PORT = "5432"

DEBUG = True


RABBITMQ_URL = 'amqp://remote:remote@localhost:5672/%2F'
NEW_TRANSACTIONS_QUEUE = 'xopay_processing'
TRANSACTION_STATUS_QUEUE = 'xopay_processing_status'


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')

# Queue:
QUEUE_HOST = 'localhost'
QUEUE_PORT = 5672
QUEUE_USERNAME = 'remote'
QUEUE_PASSWORD = 'remote'
QUEUE_NAME = 'transactions'