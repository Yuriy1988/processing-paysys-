from testing import BaseTestCase

__author__ = 'Kostel Serhii'


class ProcessingTest(BaseTestCase):

    async def test_pay_pal_incoming_payment_success(self):
        trans = self.get_transaction(paysys_id='PAY_PAL')

        await self.put_trans_for_processing(trans)
        result = await self.get_trans_status()

        self.assertIn('redirect_url', result.keys())
        self.assertEqual(result['id'], trans['id'])
        self.assertEqual(result['status'], '3D_SECURE')
