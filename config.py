
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
RABBIT_HOST = '0.0.0.0'
RABBIT_PORT = 5672
RABBIT_USERNAME = 'xopay_rabbit'
RABBIT_PASSWORD = '5lf01xiOFwyMLvQrkzz7'
RABBIT_VIRTUAL_HOST = '/xopay'

INCOME_QUEUE_NAME = 'transactions_for_processing'
OUTCOME_QUEUE_NAME = 'statuses'
