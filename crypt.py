import os
import base64
import logging
import requests
import requests.exceptions
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

from config_loader import config


def encrypt(data, key):
    cipher = PKCS1_OAEP.new(key)
    return base64.b64encode(cipher.encrypt(data.encode()))


def decrypt(b64_data, key):
    cipher = PKCS1_OAEP.new(key)
    data = base64.b64decode(b64_data)
    return cipher.decrypt(data).decode()


def debug_generate():
    key = RSA.generate(config.CRYPT_NBITS)
    config.RSA_KEY = key

    with open(config.CRYPT_DEBUG_RSA_FILE_NAME, 'wb') as f:
        f.write(key.exportKey('PEM'))

    return key


def debug_load_key():
    return RSA.importKey(open(config.CRYPT_DEBUG_RSA_FILE_NAME, 'rb').read())


def is_debug_key_exists():
    return os.path.exists(config.CRYPT_DEBUG_RSA_FILE_NAME)


def generate():
    key = RSA.generate(config.CRYPT_NBITS)
    config.RSA_KEY = key

    with open(config.CRYPT_RSA_FILE_NAME, 'wb') as f:
        f.write(key.publickey().exportKey('PEM'))

    return key


def update_public_key_on_client(new_key):

    url = config.CLIENT_API_URL + '/security/public_key'
    key_json = {"key": new_key.publickey().exportKey('PEM').decode()}

    try:
        response = requests.post(url, json=key_json)
        if response.status_code == 200:
            logging.info("Client rsa key updated successfully.")
        else:
            logging.warning("Client rsa key hasn't updated successfully.")
        return response
    except requests.exceptions.ConnectionError:
        logging.error("Client rsa key update error. Connection error.")
