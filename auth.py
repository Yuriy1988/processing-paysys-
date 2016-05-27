import jwt
from datetime import datetime

from config import config

__author__ = 'Kostel Serhii'


def _create_token(payload):
    token = jwt.encode(payload, config.AUTH_KEY, algorithm=config.AUTH_ALGORITHM)
    return token.decode('utf-8')


def get_system_token():
    """
    System token to communicate between internal services
    :return: system JWT token
    """
    payload = dict(
        exp=datetime.utcnow() + config.AUTH_TOKEN_LIFE_TIME,
        user_id=config.AUTH_SYSTEM_USER_ID,
        groups=['system'],
    )
    return _create_token(payload=payload)
