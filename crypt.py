import os
import base64
import logging
import config
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

NBITS = 2048
RSA_FILE_NAME = 'public.pem'
DEBUG_RSA_FILE_NAME = 'debug_rsa_key.pem'

HOST_NAME = '192.168.1.118:7254'
API_VERSION = 'dev'
RSA_UPDATE_API_URL = 'http://{host}/api/client/{version}/security/public_key'.format(host=HOST_NAME, version=API_VERSION)


def encrypt(data, key):
    cipher = PKCS1_OAEP.new(key)
    return base64.b64encode(cipher.encrypt(data.encode()))


def decrypt(b64_data, key):
    cipher = PKCS1_OAEP.new(key)
    data = base64.b64decode(b64_data)
    return cipher.decrypt(data).decode()


def debug_generate():
    key = RSA.generate(NBITS)
    config.RSA_KEY = key

    with open(DEBUG_RSA_FILE_NAME, 'wb') as f:
        f.write(key.exportKey('PEM'))

    return key


def debug_load_key():
    return RSA.importKey(open(DEBUG_RSA_FILE_NAME, 'rb').read())


def is_debug_key_exists():
    return os.path.exists(DEBUG_RSA_FILE_NAME)


def generate():
    key = RSA.generate(NBITS)
    config.RSA_KEY = key

    with open(RSA_FILE_NAME, 'wb') as f:
        f.write(key.publickey().exportKey('PEM'))

    return key


def update_public_key_on_client(new_key):
    url = RSA_UPDATE_API_URL
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
