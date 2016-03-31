import hashlib
import json
import logging
from random import random, randint, choice
from tornado import gen, httpclient


log = logging.getLogger(__name__)

class VisaMasterPaymentsAbstract():

    password = 'test'
    paym_system_url = 'http://test.test'

    @gen.coroutine
    def auth(self, cardnumber, cvv, expdate, merid, amount, ccy, description):
        adopt_data = self.adapt_auth_data(cardnumber, cvv, expdate, merid, amount, ccy, description)
        response = yield self.send(adopt_data, self.paym_system_url)
        return self.serialize_auth_response(response)


    @gen.coroutine
    def capture(self, cardnumber, cvv, expdate, merid, amount, ccy, description, hold_id):
        adopt_data = self.adapt_capture_data(cardnumber, cvv, expdate, merid, amount, ccy, description,hold_id)
        response = yield self.send(adopt_data, self.paym_system_url)
        return self.serialize_capture_response(response)

    @gen.coroutine
    def order_status(self, order_id):
        adopt_data = self.adapt_order_status_data(order_id)
        response = yield self.send(adopt_data)
        return self.serialize_capture_response(response)


    @gen.coroutine
    def send(self, data, url):
        http_client = httpclient.HTTPClient()
        try:
            response = http_client.fetch(url)
            print(response.body)
        except httpclient.HTTPError as e:
            # HTTPError is raised for non-200 responses; the response
            # can be found in e.response.
            print("Error: " + str(e))
        except Exception as e:
            # Other errors are possible, such as IOError.
            print("Error: " + str(e))
        http_client.close()

    def serialize_auth_response(self, response):
        return {'status': choice(['ok', 'wait', 'decline']), 'time': 1243}

    def adapt_auth_data(self, cardnumber, cvv, expdate, merid, amount, ccy, description):
        pass

    def serialize_capture_response(self, response):
        return {'status': choice(['ok', 'wait', 'decline']), 'time': 1243}

    def adapt_capture_data(self, cardnumber, cvv, expdate, merid, amount, ccy, description, hold_id):
        pass

    def adapt_order_status_data(self, order_id):
        pass

    def signature(self, data, schem, password):
        sign_list = [str(data[i]) for i in schem]
        sign_list.append(password)
        sign_str = ''.join(sign_list)
        # sign = hashlib.sha256(sign_str.encode('utf-8'))
        # sign = sign.digest()
        return sign_str


class TestPaymentSystem(VisaMasterPaymentsAbstract):

    password = 'test'

    def adapt_auth_data(self, cardnumber, cvv, expdate, merid, amount, ccy, description):
        auth_data = {'pan': cardnumber,
                     'cvv2': cvv,
                     'expdate': expdate,
                     'merid': merid,
                     'ccy': ccy,
                     'amount': amount,
                     'description': description,}
        sign = self.signature(data=auth_data,
                              schem=['pan', 'cvv2', 'expdate', 'merid', 'amount', 'ccy', 'description'],
                              password=self.password)
        auth_data['sign'] = sign

        return json.dumps(auth_data)

    def adapt_capture_data(self, cardnumber, cvv, expdate, merid, amount, ccy, description, hold_id):
        capture_data = {'hold_id': hold_id,
                     'merid': merid}
        sign = self.signature(data=capture_data,
                              schem=['hold_id', 'merid'],
                              password=self.password)
        capture_data['sign'] = sign

        return json.dumps(capture_data)

    def adapt_order_status_data(self, order_id):
        capture_data = {'order_id': order_id,}
        sign = self.signature(data=capture_data,
                              schem=['order_id'],
                              password=self.password)
        capture_data['sign'] = sign.decode('windows-1252')
        return json.dumps(capture_data)


    def serialize_auth_response(self, response):
        try:
            raw_response = json.loads(response)
        except ValueError as e:
            log.error('response is not json serializable')
            return {'status': 'wait', 'response': 'response not valid'}
        data = {'status': raw_response['status'], 'order_id': raw_response['order_id'], 'response': json.dumps(raw_response)}
        if data['status'] == '3ds':
            data['url'] = raw_response['url']
        return data

    def serialize_capture_response(self, response):
        try:
            raw_response = json.loads(response)
        except ValueError:
            log.error('response is not json serializable')
            return {'status': 'wait', 'response': 'response not valid'}
        data = {'status': raw_response['status'], 'order_id': raw_response['order_id'], 'response': json.dumps(raw_response)}
        if data['status'] == '3ds':
            data['url'] = raw_response['url']
        return data


    @gen.coroutine
    def send(self, data, url):
        time = randint(1, 10)
        yield gen.sleep(time)
        # it's a kind of magic!!!
        if randint(0, 100) > 80:
            return json.dumps({'status': '3ds', 'order_id': randint(0, 10000), 'url':'https://bank.net/gasjihglsihjgfh'})
        if randint(0, 100) > 90:
            return json.dumps({'status': 'decline', 'order_id': randint(0, 10000)})
        if randint(0, 100) > 80:
            return json.dumps({'status': 'wait', 'order_id': randint(0, 10000)})
        return json.dumps({'status': 'ok', 'order_id': randint(0, 10000)})
