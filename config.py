from datetime import timedelta

class Debug:
    LOG_CONFIG = 'log_config.json'

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

    CRYPT_NBITS = 2048
    CRYPT_RSA_FILE_NAME = 'public.pem'
    CRYPT_DEBUG_RSA_FILE_NAME = 'debug_rsa_key.pem'

    CLIENT_API_URL = 'http://127.0.0.1:7254/api/client/dev'

    AUTH_ALGORITHM='HS512'
    AUTH_KEY='PzYs2qLh}2$8uUJbBnWB800iYKe5xdYqItRNo7@38yW@tPDVAX}EV5V31*ZK78QS'
    AUTH_TOKEN_LIFE_TIME=timedelta(minutes=30)
    AUTH_SYSTEM_USER_ID='xopay.processing'

    WAIT_BEFORE_SHUTDOWN_SEC = 3


class Production(Debug):

    DEBUG = False

    CLIENT_API_URL = 'https://xopay.digitaloutlooks.com/api/client/dev'


class Testing(Debug):
    RABBIT_HOST = '127.0.0.1'
    RABBIT_PORT = 5672
    INCOME_QUEUE_NAME = 'test_transactions_for_processing'
    OUTCOME_QUEUE_NAME = 'test_statuses'
    DB_NAME = "test_processing_db"
