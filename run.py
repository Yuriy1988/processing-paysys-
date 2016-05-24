import json

from datetime import timedelta

import motor
import signal
import logging
import logging.config
from tornado.ioloop import IOLoop

import crypt
import config_loader
from app.processing import Processing


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
    logging.info("Stopping processing...")
    processing.stop()
    ioloop = IOLoop.current()

    def finalize():
        ioloop.stop()
        logging.info("Service stopped!")

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

    with open(config.LOG_CONFIG, 'rt') as f:
        log_config = json.load(f)
    logging.config.dictConfig(log_config)
    logging.getLogger("production")

    main()
