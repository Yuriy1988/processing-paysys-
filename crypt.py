import os
import base64
import logging
import asyncio
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

import utils
from config import config

_log = logging.getLogger('xop.crypt')


def encrypt(data, key):
    cipher = PKCS1_OAEP.new(key)
    return base64.b64encode(cipher.encrypt(data.encode()))


def decrypt(b64_data, key):
    cipher = PKCS1_OAEP.new(key)
    data = base64.b64decode(b64_data)
    return cipher.decrypt(data).decode()


def _generate_rsa_key():
    """
    Generate RSA key depending of config settings.
    In DEBUG mode load existing key from file.
    :return: RSA key string
    """
    if config['DEBUG'] and os.path.exists(config['CRYPT_RSA_FILE_NAME']):
        with open(config['CRYPT_RSA_FILE_NAME'], 'rb') as lf:
            return RSA.importKey(lf.read())

    key = RSA.generate(config['CRYPT_NBITS'])

    with open(config['CRYPT_RSA_FILE_NAME'], 'wb') as gf:
        if config['DEBUG']:
            gf.write(key.exportKey('PEM'))
        else:
            gf.write(key.publickey().exportKey('PEM'))

    return key


async def _update_public_key_on_client(new_key):
    resp_body, error = await utils.http_request(
        url=config['CLIENT_API_URL'] + '/security/public_key',
        method='POST',
        body={"key": new_key.publickey().exportKey('PEM').decode()}
    )
    if error:
        _log.critical('Error update client RSA key: %s', error)
    else:
        _log.info('Client rsa key updated successfully')


def create_rsa_key():
    rsa_key = _generate_rsa_key()
    asyncio.ensure_future(_update_public_key_on_client(rsa_key))
    return rsa_key
