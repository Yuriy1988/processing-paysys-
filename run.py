#!venv/bin/python

import os
import motor
import json
import signal
import logging
import logging.handlers
from datetime import timedelta
from tornado.ioloop import IOLoop

import crypt
import config_loader
from app.processing import Processing


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


def rsa_setup():
    if config.DEBUG:
        if crypt.is_debug_key_exists():
            config.RSA_KEY = crypt.debug_load_key()
        else:
            config.RSA_KEY = crypt.debug_generate()
    else:
        config.RSA_KEY = crypt.generate()
    crypt.update_public_key_on_client(config.RSA_KEY)


def shutdown(processing):
    log = logging.getLogger('xop.shutdown')

    log.info("Stopping processing...")
    processing.stop()
    ioloop = IOLoop.current()

    def finalize():
        ioloop.stop()
        log.info("Service stopped!")

    wait_sec = config.WAIT_BEFORE_SHUTDOWN_SEC

    if wait_sec:
        ioloop.add_timeout(timedelta(seconds=wait_sec), finalize)
    else:
        finalize()


def main():
    db = getattr(motor.MotorClient(), config.DB_NAME)
    rsa_setup()
    p = Processing(db=db)
    p.init(ioloop=IOLoop.current())

    signal.signal(signal.SIGINT, lambda sig, frame: shutdown(p))
    signal.signal(signal.SIGTERM, lambda sig, frame: shutdown(p))

    IOLoop.current().start()


if __name__ == '__main__':
    config = config_loader.config
    config.load_from_file("config", "Production")

    logger_configure(config)

    main()
