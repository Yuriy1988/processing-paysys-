import jwt
import json
import logging
import aiohttp
from datetime import datetime

from asyncio import TimeoutError
from aiohttp.errors import ClientError
from json.decoder import JSONDecodeError

from config import config

__author__ = 'Kostel Serhii'


_log = logging.getLogger('xop.utils')


# Auth

def _create_token(payload):
    token = jwt.encode(payload, config['AUTH_KEY'], algorithm=config['AUTH_ALGORITHM'])
    return token.decode('utf-8')


def get_system_token():
    """
    System token to communicate between internal services
    :return: system JWT token
    """
    payload = dict(
        exp=datetime.utcnow() + config['AUTH_TOKEN_LIFE_TIME'],
        user_id=config['AUTH_SYSTEM_USER_ID'],
        groups=['system'],
    )
    return _create_token(payload=payload)


# Services HTTP Request

async def http_request(url, method='GET', body=None, params=None, headers=None, auth_token=None, auth=None):
    """
    Create async http request to the REST API XOP Services.
    Work only with json objects.
    :param url: request url
    :param method: one of: GET, PUT, POST, DELETE
    :param body: dict with request body for PUT or POST
    :param params: dict with request url arguments
    :param headers: dict with headers
    :param auth_token: string with token or None (not auth)
    :param auth: dict with auth login and password
    :return: tuple (response body dict, error message)
    """
    headers = headers or {}

    if auth_token is not None:
        if auth_token == 'system':
            auth_token = get_system_token()
        headers['Authorization'] = 'Bearer %s' % auth_token

    if auth is not None:
        auth = aiohttp.BasicAuth(**auth)

    if isinstance(body, dict):
        body = json.dumps(body)
        headers['Content-Type'] = 'application/json'

    try:
        with aiohttp.ClientSession() as session:
            with aiohttp.Timeout(10):
                async with session.request(
                        method,
                        url,
                        data=body,
                        params=params,
                        headers=headers,
                        auth=auth) as response:
                    rest_status = response.status
                    resp_body = await response.json()

    except (JSONDecodeError, TypeError) as err:
        err_msg = 'HTTP bad response error: %r' % err
        _log.error(err_msg)
        return None, err_msg
    except (TimeoutError, ClientError) as err:
        err_msg = 'HTTP request error: %r' % err
        _log.critical(err_msg)
        return None, err_msg

    if rest_status != 200:
        err_msg = 'HTTP wrong status %d. Error detail: %r' % (rest_status, resp_body)
        _log.error(err_msg)
        return None, err_msg

    return resp_body, None
