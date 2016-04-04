import json
import logging

import config
from processing import crypt


log = logging.getLogger(__name__)


def visa_master_serializer(data=None):
    if not data:
        raise ValueError
    decrypted_data = crypt.decryypt(data, config.SECRET_KEY)
    card_number = decrypted_data.get('cardnumber')
    expdate = decrypted_data.get('expdate')
    cvv = decrypted_data.get('cvv')
    cardholder_name = decrypted_data.get('cardholder_name')
    if cardholder_name and card_number and expdate and cvv:
        return {'cardnumber': card_number,
                'cvv': cvv,
                'expdate': expdate,
                'cardholder_name': cardholder_name}
    log.error('SOURCE data corrupted')
    raise ValueError


def paypal_serializer(data=None):
    if not data:
        raise ValueError
    return data


def bitcoin_serializer(data=None):
    if not data:
        raise ValueError

    return data


transaction_source_serializers = {
    'credit_card': visa_master_serializer,
    'paypal': paypal_serializer,
    'bitcoin': bitcoin_serializer
}


def request_serialazer(request):

    data = json.loads(request)
    transaction_uuid = data.get('id')
    transaction_type = data.get('payment_type')   # type of paymen system VISA bitcoin paypal
    transaction_source_serializer = transaction_source_serializers.get(transaction_type)
    transaction_currency = data.get('currency')
    transaction_amount = data.get('amount')
    if not transaction_source_serializer or not transaction_currency or not transaction_amount \
            or transaction_currency not in config.CURRENCY_LIST:
        raise ValueError
    transaction_amount = int(transaction_amount)
    temp_source = data.get('source')
    transaction_source_merchant_data = {'paysys_id': temp_source.get('paysys_id'),
                                        'contract': temp_source.get('contract'),
                                        'merid': temp_source['contract']['merid']}
    transaction_source = transaction_source_serializer(temp_source.get('data'))
    transaction_destination = destination_serializer(data.get('destination'))
    return {'type': transaction_type,
            'source': transaction_source,
            'source_merchant_data': transaction_source_merchant_data,
            'destination': transaction_destination,
            'description': data.get('description', ''),
            'amount': transaction_amount,
            'currency': transaction_currency,
            'uuid': transaction_uuid}


def destination_serializer(destination_data):
    if not destination_data:
        raise ValueError
    return destination_data
