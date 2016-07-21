import os
import logging
import logging.handlers
from datetime import timedelta


class debug:

    DEBUG = True
    UPDATE_RSA_KEY = True

    DB_NAME = "processing_db"

    # Queue:
    QUEUE_HOST = '127.0.0.1'
    QUEUE_PORT = 5672
    QUEUE_USERNAME = 'xopay_rabbit'
    QUEUE_VIRTUAL_HOST = '/xopay'
    QUEUE_PASSWORD = '5lf01xiOFwyMLvQrkzz7'

    QUEUE_TRANS_FOR_PROCESSING = 'transactions_for_processing'
    QUEUE_TRANS_STATUS = 'transactions_status'
    QUEUE_3D_SECURE_RESULT = '3d_secure_result'

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

    CRYPT_NBITS = 2048
    CRYPT_RSA_FILE_NAME = 'debug_rsa_key.pem'


class test(debug):

    DEBUG = True
    UPDATE_RSA_KEY = False

    LOG_ROOT_LEVEL = 'WARNING'
    LOG_LEVEL = 'WARNING'

    DB_NAME = "test_processing_db"

    QUEUE_VIRTUAL_HOST = '/xopay_test'


class production(debug):

    DEBUG = False
    UPDATE_RSA_KEY = True

    LOG_ROOT_LEVEL = 'INFO'
    LOG_LEVEL = 'INFO'

    LOG_FILE = '/var/log/xopay/xopay.log'
    LOG_MAX_BYTES = 10*1024*1024
    LOG_BACKUP_COUNT = 10

    QUEUE_HOST = 'xopay.digitaloutlooks.com'

    ADMIN_API_URL = 'https://xopay.digitaloutlooks.com/api/admin/dev'
    CLIENT_API_URL = 'https://xopay.digitaloutlooks.com/api/client/dev'

    CRYPT_RSA_FILE_NAME = 'public.pem'


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


class _ConfigLoader(dict):
    """ Load config with config_name."""

    def __init__(self):
        super().__init__()

    def load_config(self, config_name='debug'):
        """
        :param config_name: one of the class names in current module
        """
        xop_config_obj = globals()[config_name]
        if not xop_config_obj:
            return

        config_instance = xop_config_obj()
        for key in dir(config_instance):
            if key.isupper():
                self[key] = getattr(config_instance, key)


config = _ConfigLoader()
