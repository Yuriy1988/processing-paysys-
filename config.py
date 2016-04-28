# import logging

# TODO: move to tornado options
# TODO: divide debug and production logging

# TODO: routing by BIN
# TODO: add store PI


class Debug:
    LOG_CONFIG = 'log.json'

    RSA_KEY = None

    CURRENCY_LIST = ['EUR', 'USD', 'UAH', 'RUR']

    DB_NAME = "processing_db"

    DEBUG = True

    # Queue:
    RABBIT_HOST = 'xopay.digitaloutlooks.com'
    RABBIT_PORT = 5672
    RABBIT_USERNAME = 'xopay_rabbit'
    RABBIT_PASSWORD = '5lf01xiOFwyMLvQrkzz7'
    RABBIT_VIRTUAL_HOST = '/xopay'

    INCOME_QUEUE_NAME = 'transactions_for_processing'
    OUTCOME_QUEUE_NAME = 'transactions_status'

    WAIT_BEFORE_SHUTDOWN_SEC = 3


class Testing(Debug):
    RABBIT_HOST = '127.0.0.1'
    RABBIT_PORT = 5672
    INCOME_QUEUE_NAME = 'test_transactions_for_processing'
    OUTCOME_QUEUE_NAME = 'test_statuses'
    DB_NAME = "test_processing_db"
