
SECRET_KEY = 'kasjkfhgqawoif'
PUBLIC_KEY = 'kasjkfhgqawoif'

CURRENCY_LIST = ['EUR', 'USD', 'UAH', 'RUR']

DB_USER = "xopayadmin3"
DB_USER_PASSWORD = "xopay"
DB_NAME = "xopayprocessing3"
DB_HOST = "localhost"
DB_PORT = "5432"

DEBUG = True


RABBITMQ_URL = 'amqp://remote:remote@localhost:5672/%2F'
NEW_TRANSACTIONS_QUEUE = 'xopay_processing'
TRANSACTION_STATUS_QUEUE = 'xopay_processing_status'
# PROCESSING_REQUEST_QUEUE = 'xopay_processing'
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'





LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')