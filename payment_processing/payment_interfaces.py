from copy import deepcopy

import store_interfaces

__author__ = 'Kostel Serhii'


class PaymentInterfaceError(Exception):
    pass


class PaymentInterface(object):
    """Abstract class for payment interfaces."""

    TRANSACTION_STATUS_ENUM = ('3D_SECURE', 'PROCESSED', 'SUCCESS', 'REJECTED')

    def __init__(self, transaction):
        self.transaction = deepcopy(transaction)

    async def process_transaction(self):
        """
        Async transaction processing method.
        :return: tuple (status, extra_info) of the transaction
        """
        raise NotImplementedError('Transaction processor not implemented.')

    # TODO: complete store interfaces

    async def auth_source(self):
        if not store_interfaces.check(self.transaction):
            raise PaymentInterfaceError("Store checking failed.")

    async def capture_source(self):
        store_interfaces.withdraw(self.transaction)


class PayPal(PaymentInterface):

    async def process_transaction(self):
        return 'REJECTED', {'rejected_detail': 'Not Implemented'}


class BitCoin(PaymentInterface):

    async def process_transaction(self):
        return 'REJECTED', {'rejected_detail': 'Not Implemented'}


class VisaMaster(PaymentInterface):

    def auth_destination(self):
        pass

    def capture_destination(self):
        pass

    def void(self):
        pass

    async def process_transaction(self):
        return 'REJECTED', {'rejected_detail': 'Not Implemented'}


paysys_interface_mapper = {
    'PAY_PAL': PayPal,
    'BIT_COIN': BitCoin,
    'VISA_MASTER': VisaMaster,
}


def get_payment_interface(transaction):
    """
    Return payment interface for current transaction
    :param transaction: transaction dict
    :return: payment interface class instance
    """
    paysys_id = transaction['payment']['paysys_id']
    payment_interface = paysys_interface_mapper.get(paysys_id)

    if payment_interface is None:
        raise PaymentInterfaceError('Payment interface "%s" not found' % paysys_id)

    return payment_interface(transaction)
