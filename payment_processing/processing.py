import logging

from .payment_interfaces import get_payment_interface

__author__ = 'Kostel Serhii'

_log = logging.getLogger('xop.payment')


class Processing(object):

    def __init__(self, db, results_handler):
        """
        Create processing instance.
        Save db connector and
        async callback for processing transaction result
        :param db: connection to the db
        :param results_handler: async method to send transaction status result
        """
        self.db = db
        self.result_handler = results_handler

    async def db_load(self, trans_id):
        """
        Load transaction from db
        :param trans_id: transaction identifier
        :return: transaction dict
        """
        _log.debug('Load transaction [%s] from DB', trans_id)
        transaction = await self.db.transaction.find_one({'id': trans_id})
        transaction.pop('_id', None)
        return transaction

    async def db_save(self, transaction):
        """
        Create or update transaction into db
        :param transaction: transaction dict
        """
        _log.debug('Save transaction [%s] to DB', transaction['id'])
        await self.db.transaction.update({'id': transaction['id']}, {'$set': transaction}, upsert=True)

    async def update(self, transaction, status, extra_info=None):
        """
        Update transaction status and extra info.
        NOTE: do not update ant onter transaction information
        :param transaction: transaction dict
        :param status: transaction status
        :param extra_info: transaction extra info
        """
        _log.info('Update transaction [%s] status to "%s" and extra info "%s"',
                  transaction['id'], status, extra_info or '')

        transaction['payment']['status'] = status

        if extra_info:
            trans_extra_info = transaction.get('extra_info') or {}
            trans_extra_info.update(extra_info)
            transaction['extra_info'] = trans_extra_info

        await self.db_save(transaction)

    @staticmethod
    def form_response(transaction):
        response = {
            'id': transaction['id'],
            'status': transaction['payment']['status']
        }
        extra_info = transaction.get('extra_info')
        response.update(extra_info or {})
        return response

    async def transaction_handler(self, transaction):
        """
        Transaction queue handler.

        Receive transaction dict from queue.
        Get and process it by payment interface.
        Update transaction and send response to queue.
        Reject transaction on error.

        :param transaction: transaction dict
        """
        trans_id = transaction.get('id', 'Unknown')
        _log.info('Receive transaction [%s]', trans_id)

        await self.db_save(transaction)

        try:
            payment_interface = get_payment_interface(transaction)
            _log.info('Start transaction [%s] processing', trans_id)
            status, extra_info = await payment_interface.process_transaction()
            await self.update(transaction, status, extra_info)

        except Exception as err:
            _log.exception('Error transaction [%s] processing: %s', trans_id, str(err))
            await self.update(transaction, 'REJECTED', {'rejected_detail': str(err)})

        finally:
            _log.info('Send transaction [%s] status "%s" to queue', trans_id, transaction['payment']['status'])
            await self.result_handler(self.form_response(transaction))

    async def response_3d_secure_handler(self, message):
        """
        3D secure queue handler.

        Load transaction from DB.
        If pay result = cancel -> Reject transaction.
        If pay result = success -> Continue transaction flow.

        :param message: 3D secure result dict
        """
        trans_id = message.get('trans_id', '')
        transaction = await self.db_load(trans_id)
        if not transaction:
            _log.error('Transaction for 3D secure message [%s] not found', message)
            return

        pay_result = message.get('pay_result', '').lower()

        if pay_result == 'success':
            await self.update(transaction, 'PROCESSED', message.get('extra_info'))
            await self.transaction_handler(transaction)

        elif pay_result == 'cancel':
            await self.update(transaction, 'REJECTED', message.get('extra_info'))
            await self.update(transaction, 'REJECTED', {'rejected_detail': 'Cancelled by 3D secure server'})
            await self.result_handler(self.form_response(transaction))

        else:
            _log.error('Wrong 3D secure pay result "%s"', pay_result)
