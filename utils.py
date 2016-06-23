import json
import logging
import aiohttp

from asyncio import TimeoutError
from aiohttp.errors import ClientError
from json.decoder import JSONDecodeError

import auth

__author__ = 'Kostel Serhii'


_log = logging.getLogger('xop.utils')


async def http_request(url, method='GET', body=None, params=None):
    """
    Create async http request to the REST API.
    Work only with json objects.
    :param url: request url
    :param method: one of: GET, PUT, POST, DELETE
    :param body: dict with request body for PUT or POST
    :param params: dict with request url arguments
    :return: tuple (response body dict, error message)
    """
    data = json.dumps(body)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer %s' % auth.get_system_token()
    }

    try:
        with aiohttp.ClientSession() as session:
            with aiohttp.Timeout(10):
                async with session.request(method, url, data=data, params=params, headers=headers) as response:
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
