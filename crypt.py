import os
import json
import base64
import logging
import requests
import requests.exceptions
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

import auth
from config import config


_log = logging.getLogger('xop.crypt')


def encrypt(data, key):
    cipher = PKCS1_OAEP.new(key)
    return base64.b64encode(cipher.encrypt(data.encode()))


def decrypt(b64_data, key):
    cipher = PKCS1_OAEP.new(key)
    data = base64.b64decode(b64_data)
    return cipher.decrypt(data).decode()


def debug_generate():
    key = RSA.generate(config['CRYPT_NBITS'])
    config['RSA_KEY'] = key

    with open(config['CRYPT_DEBUG_RSA_FILE_NAME'], 'wb') as f:
        f.write(key.exportKey('PEM'))

    return key


def debug_load_key():
    return RSA.importKey(open(config['CRYPT_DEBUG_RSA_FILE_NAME'], 'rb').read())


def is_debug_key_exists():
    return os.path.exists(config['CRYPT_DEBUG_RSA_FILE_NAME'])


def generate():
    key = RSA.generate(config['CRYPT_NBITS'])
    config['RSA_KEY'] = key

    with open(config['CRYPT_RSA_FILE_NAME'], 'wb') as f:
        f.write(key.publickey().exportKey('PEM'))

    return key


def update_public_key_on_client(new_key):

    url = config['CLIENT_API_URL'] + '/security/public_key'
    key_json = {"key": new_key.publickey().exportKey('PEM').decode()}
    data = json.dumps(key_json)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer %s' % auth.get_system_token()
    }

    try:
        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            _log.info("Client rsa key updated successfully.")
        else:
            _log.warning("Client rsa key hasn't updated successfully.")
        return response
    except requests.exceptions.ConnectionError:
        _log.error("Client rsa key update error. Connection error.")


def rsa_setup():
    if config['DEBUG']:
        if is_debug_key_exists():
            config['RSA_KEY'] = debug_load_key()
        else:
            config['RSA_KEY'] = debug_generate()
    else:
        config['RSA_KEY'] = generate()

    update_public_key_on_client(config['RSA_KEY'])
