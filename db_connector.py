from tornado import gen


class DBConnection():

    def __init__(self, db):
        self.db = db

    @gen.coroutine
    def db_execute(self, sql, insert_data):
        cursor = yield self.db.execute(sql, insert_data)
        cursor_id = cursor.fetchone()
        cursor.close()
        return cursor_id[0]

    @gen.coroutine
    def db_update_status(self, id, status):
        cursor = yield self.db.execute('UPDATE transactions SET status=%s WHERE id=%s;', (status, id))
        return cursor

    @gen.coroutine
    def db_add_auth_response(self, id, auth_source_response, source_hold_id):
        cursor = yield self.db.execute('UPDATE transactions SET source_auth_response=%s, source_hold_id=%s WHERE id=%s;',
                                       (auth_source_response, source_hold_id, id))
        return cursor

    @gen.coroutine
    def db_add_capture_response(self, id, capture_source_response, source_order_id):
        cursor = yield self.db.execute('UPDATE transactions SET source_capture_response=%s, source_order_id=%s WHERE id=%s;',
                                       (capture_source_response, source_order_id, id))
        return cursor

    @gen.coroutine
    def db_select_status(self, id):
        cursor = yield self.db.execute('SELECT status FROM transactions WHERE id=%s;', (id,))
        return cursor.fetchone()[0]

    @gen.coroutine
    def db_insert_transacton(self, transaction_data):
        cursor = yield self.db.execute("""INSERT INTO transactions (status, amount, source, currency, destination, description, uuid, source_merchant_data)
                                          VALUES (%(status)s, %(amount)s, %(source)s, %(currency)s, %(destination)s, %(description)s, %(uuid)s, %(source_merchant_data)s) RETURNING ID;""",
                                                 transaction_data)
        return cursor.fetchone()[0]