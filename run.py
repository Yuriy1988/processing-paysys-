import motor
from processing.processing import Processing
from tornado.ioloop import IOLoop

import config
import crypt


def rsa_setup():
    if config.DEBUG:
        if crypt.is_debug_key_exists():
            config.RSA_KEY = crypt.debug_load_key()
        else:
            config.RSA_KEY = crypt.debug_generate()
    else:
        config.RSA_KEY = crypt.generate()
    crypt.update_public_key_on_client(config.RSA_KEY)


if __name__ == '__main__':
    db = getattr(motor.MotorClient(), config.DB_NAME)
    rsa_setup()
    p = Processing(db=db)
    p.init(ioloop=IOLoop.current())
    IOLoop.current().start()
