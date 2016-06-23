import os
import importlib
import argparse
import logging
import logging.handlers
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
    CRYPT_RSA_FILE_NAME = 'debug_rsa_key.pem'

    CLIENT_API_URL = 'http://127.0.0.1:7254/api/client/dev'

    LOG_BASE_NAME = 'xop'
    LOG_FORMAT = 'PROCESS| %(levelname)-6.6s | %(name)-15.15s | %(asctime)s | %(message)s'
    LOG_DATE_FORMAT = '%d.%m %H:%M:%S'

    LOG_ROOT_LEVEL = 'DEBUG'
    LOG_LEVEL = 'DEBUG'

    AUTH_ALGORITHM='HS512'
    AUTH_KEY='PzYs2qLh}2$8uUJbBnWB800iYKe5xdYqItRNo7@38yW@tPDVAX}EV5V31*ZK78QS'
    AUTH_TOKEN_LIFE_TIME=timedelta(minutes=30)
    AUTH_SYSTEM_USER_ID='xopay.processing'

    WAIT_BEFORE_SHUTDOWN_SEC = 3


class Production(Debug):

    DEBUG = False

    LOG_ROOT_LEVEL = 'INFO'
    LOG_LEVEL = 'INFO'

    LOG_FILE = '/var/log/xopay/xopay.log'
    LOG_MAX_BYTES = 10*1024*1024
    LOG_BACKUP_COUNT = 10

    CLIENT_API_URL = 'https://xopay.digitaloutlooks.com/api/client/dev'

    CRYPT_RSA_FILE_NAME = 'public.pem'


class Testing(Debug):

    LOG_ROOT_LEVEL = 'INFO'
    LOG_LEVEL = 'INFO'

    RABBIT_HOST = '127.0.0.1'
    RABBIT_PORT = 5672

    INCOME_QUEUE_NAME = 'test_transactions_for_processing'
    OUTCOME_QUEUE_NAME = 'test_statuses'

    DB_NAME = "test_processing_db"


def logger_configure(log_config):

    if 'LOG_FILE' in log_config and os.access(os.path.dirname(log_config['LOG_FILE']), os.W_OK):
        log_handler = logging.handlers.RotatingFileHandler(
            filename=log_config['LOG_FILE'],
            maxBytes=log_config['LOG_MAX_BYTES'],
            backupCount=log_config['LOG_BACKUP_COUNT'],
            encoding='utf8',
        )
    else:
        log_handler = logging.StreamHandler()

    log_formatter = logging.Formatter(fmt=log_config['LOG_FORMAT'], datefmt=log_config['LOG_DATE_FORMAT'])
    log_handler.setFormatter(log_formatter)

    # root logger
    logging.getLogger('').addHandler(log_handler)
    logging.getLogger('').setLevel(log_config['LOG_ROOT_LEVEL'])

    # local logger
    logging.getLogger(log_config.get('LOG_BASE_NAME', '')).setLevel(log_config['LOG_LEVEL'])


class ConfigLoader(dict):

    def __init__(self, *args, **kwargs):
        super(ConfigLoader, self).__init__(*args, **kwargs)
        self._load_config_from_args()

    def _load_config_from_args(self):
        parser = argparse.ArgumentParser(description='XOPay Processing Service.', allow_abbrev=False)
        parser.add_argument('--debug', action='store_true', default=False, help='run in debug mode')

        args = parser.parse_args()
        if args.debug:
            self.load_from_object(Debug)
        else:
            self.load_from_object(Production)

    def load_from_file(self, filename, objname=None):
        m = importlib.import_module(filename)
        if objname:
            self.load_from_object(getattr(m, objname))
        else:
            self.load_from_object(m)

    def load_from_object(self, obj):
        self.update({key: getattr(obj, key) for key in filter(
            lambda x: not callable(getattr(obj, x)) and not x.startswith("_"), dir(obj))})
        logger_configure(self)

    def __getattr__(self, item):
        if item not in dir(self):
            return self.get(item)
        else:
            return super().__getattribute__(item)


config = ConfigLoader()
