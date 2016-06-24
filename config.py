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
    QUEUE_HOST = '127.0.0.1'
    QUEUE_PORT = 5672
    QUEUE_USERNAME = 'xopay_rabbit'
    QUEUE_VIRTUAL_HOST = '/xopay'
    QUEUE_PASSWORD = '5lf01xiOFwyMLvQrkzz7'

    QUEUE_TRANS_FOR_PROCESSING = 'transactions_for_processing'
    QUEUE_TRANS_STATUS = 'transactions_status'
    QUEUE_3D_SECURE_RESULT = '3d_secure_result'

    CRYPT_NBITS = 2048
    CRYPT_RSA_FILE_NAME = 'debug_rsa_key.pem'

    ADMIN_API_URL = 'http://127.0.0.1:7128/api/admin/dev'
    CLIENT_API_URL = 'http://127.0.0.1:7254/api/client/dev'

    LOGGER_NAME = 'xop'
    LOG_FORMAT = '%(levelname)-6.6s | PROCESS| %(name)-12.12s | %(asctime)s | %(message)s'
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

    QUEUE_HOST = 'xopay.digitaloutlooks.com'

    ADMIN_API_URL = 'https://xopay.digitaloutlooks.com/api/admin/dev'
    CLIENT_API_URL = 'https://xopay.digitaloutlooks.com/api/client/dev'

    CRYPT_RSA_FILE_NAME = 'public.pem'


class Testing(Debug):

    LOG_ROOT_LEVEL = 'INFO'
    LOG_LEVEL = 'INFO'

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
    logging.getLogger(log_config.get('LOGGER_NAME', '')).setLevel(log_config['LOG_LEVEL'])


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
