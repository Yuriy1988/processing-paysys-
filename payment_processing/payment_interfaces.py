import logging

import hashlib
from copy import deepcopy

import utils
from config import config
from crypt import decode_crypted_payment

__author__ = 'Kostel Serhii'


class PaymentInterfaceError(Exception):
    pass


class PaymentInterface(object):
    """Abstract class for payment interfaces."""

    TRANSACTION_STATUS_ENUM = ('CREATED', 'ACCEPTED', '3D_SECURE', 'PROCESSED', 'SUCCESS', 'REJECTED')

    def __init__(self, transaction, db=None):
        self.transaction = deepcopy(transaction)
        self.db = db

    async def process_transaction(self):
        """
        Async transaction processing method.
        :return: tuple (status, extra_info) of the transaction
        """
        raise NotImplementedError('Transaction processor not implemented.')

    # TODO: complete store interfaces

    async def auth_source(self):
        pass
        # if not store_interfaces.check(self.transaction):
        #     raise PaymentInterfaceError("Store checking failed.")

    async def capture_source(self):
        pass
        # store_interfaces.withdraw(self.transaction)


class PayPal(PaymentInterface):
    """
    PayPal Payment Interface.
    Link: https://developer.paypal.com/docs/integration/web/accept-paypal-payment/
    """
    debug_login = "AQkquBDf1zctJOWGKWUEtKXm6qVhueUEMvXO_-MCI4DQQ4-LWvkDLIN2fGsd"
    debug_password = "EL1tVxAjhT7cJimnz5-Nsx9k2reTKSVfErNQF-CmrwJgxRtylkGTKlU4RvrX"

    log = logging.getLogger('xop.pay_pal')

    async def _get_pasys_account(self):
        """
        Get from Admin Service paysys login and password
        :return: tuple(login, password)
        """
        if config['DEBUG']:
            return self.debug_login, self.debug_password

        resp_body, error = await utils.http_request(
            url=config['ADMIN_API_URL'] + '/payment_systems/pay_pal/account',
            auth_token='system'
        )
        if error:
            raise PaymentInterfaceError(error)

        if not resp_body['active']:
            raise PaymentInterfaceError('PayPal payment interface does not active')

        return resp_body['paysys_login'], resp_body['paysys_password']

    async def _get_auth_token(self):
        """Get PayPal token."""

        # TODO: add token hash
        login, password = await self._get_pasys_account()

        resp_body, error = await utils.http_request(
            url='https://api.sandbox.paypal.com/v1/oauth2/token?grant_type=client_credentials',
            method='POST',
            headers={'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'},
            auth={'login': login, 'password': password},
            body='grant_type=client_credentials'
        )
        if error:
            raise PaymentInterfaceError(error)

        access_token = resp_body['access_token']
        return access_token

    @staticmethod
    async def _create_payment(token, trans_id, total_amount, currency, description):
        """Create PayPal payment and return approval url."""

        total_amount = '%.2f' % total_amount if isinstance(total_amount, (float, int)) else total_amount

        resp_body, error = await utils.http_request(
            url='https://api.sandbox.paypal.com/v1/payments/payment',
            method='POST',
            auth_token=token,
            body={
                'transactions': [
                    {
                        'amount': {
                            'currency': currency,
                            'total': total_amount,
                        },
                        'description': description
                    }
                ],
                'payer': {
                    'payment_method': 'paypal'
                },
                'intent': 'sale',
                'redirect_urls': {
                    'cancel_url': config['CLIENT_API_URL'] + '/3d-secure/transaction/%s/%s' % (trans_id, 'cancel'),
                    'return_url': config['CLIENT_API_URL'] + '/3d-secure/transaction/%s/%s' % (trans_id, 'success')
                }
            }
        )
        if error:
            raise PaymentInterfaceError(error)

        approval_url = next(link['href'] for link in resp_body['links'] if link.get('rel') == 'approval_url')
        return approval_url

    @staticmethod
    async def _execute_payment(token, payment_id, payer_id):
        """Execute PayPal payment."""

        resp_body, error = await utils.http_request(
            url='https://api.sandbox.paypal.com/v1/payments/payment/%s/execute' % payment_id,
            method='POST',
            auth_token=token,
            body={'payer_id': payer_id}
        )
        if error:
            raise PaymentInterfaceError(error)

    async def process_transaction(self):
        """
        Process transaction with PayPal.
        :return: tuple(status, extra_info dict)
        """
        status = self.transaction['payment']['status']
        trans_id = self.transaction['id']

        if status in ('CREATED', 'ACCEPTED'):

            self.log.info('Get PayPal token (Step 1 of 7)')
            token = await self._get_auth_token()

            self.log.info('Auth source (Step 2 of 7)')
            await self.auth_source()

            self.log.info('Create PayPal payment for transaction [%s] (Step 3 of 7)', trans_id)
            total_amount = self.transaction['payment']['invoice']['total_price']
            currency = self.transaction['payment']['invoice']['currency']
            description = self.transaction['payment']['description']
            approval_url = await self._create_payment(token, trans_id, total_amount, currency, description)

            self.log.info('Send PayPal 3D secure redirect for transaction [%s] (Step 4 of 7)', trans_id)
            return '3D_SECURE', {'redirect_url': approval_url}

        elif status in ('3D_SECURE', 'PROCESSED'):

            self.log.info('Capture source (Step 5 of 7)')
            await self.capture_source()

            self.log.info('Execute PayPal payment for transaction [%s] (Step 6 of 7)', trans_id)
            token = await self._get_auth_token()
            payment_id = self.transaction['extra_info']['paymentId']
            payer_id = self.transaction['extra_info']['PayerID']
            await self._execute_payment(token, payment_id, payer_id)

            self.log.info('Send PayPal payment success state for transaction [%s] (Step 7 of 7)', trans_id)
            return 'SUCCESS', None

        elif status in ('SUCCESS', 'REJECTED'):
            return status, None

        error_msg = 'Wrong transaction status "%s"', status
        self.log.error(error_msg)
        return 'REJECTED', {'rejected_detail': error_msg}


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

        # --- ANTIFRAUD pre-processing ---
        payment_info = decode_crypted_payment(self.transaction["source"]["payment_requisites"]["crypted_payment"])
        pay_acc_hash = hashlib.sha256(payment_info("card_number").encode()).hexdigest()

        if self.db.blacklist.find_one({"pay_acc": pay_acc_hash}):
            return 'REJECTED', {'rejected_detail': 'Found in blacklist.'}

        del payment_info, pay_acc_hash  # clean up sensitive data

        # Decide 3D secure or not depends on the score
        THRESHOLD = 0
        if self.transaction["extra_info"]["antifraud_score"] > THRESHOLD:
            return '3D_SECURE', {'redirect_url': 'Some url'}  # TODO real URL for 3d_secure
        # --- END ANTIFRAUD ---

        pass

        return 'REJECTED', {'rejected_detail': 'Not Implemented'}


paysys_interface_mapper = {
    'PAY_PAL': PayPal,
    'BIT_COIN': BitCoin,
    'VISA_MASTER': VisaMaster,
}


def get_payment_interface(paysys_id):
    """
    Return payment interface for current transaction
    :param paysys_id: payment system id (paysys_interface_mapper keys)
    :return: payment interface class instance
    """
    payment_interface = paysys_interface_mapper.get(paysys_id)

    if payment_interface is None:
        raise PaymentInterfaceError('Payment interface "%s" not found' % paysys_id)

    return payment_interface
