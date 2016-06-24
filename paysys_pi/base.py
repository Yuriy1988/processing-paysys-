import store_api


class ProcessingException(Exception):
    pass


class BasePI:

    @staticmethod
    def auth_destination(transaction):
        return transaction

    @staticmethod
    def auth_source(transaction):
        if not store_api.check(transaction):
            raise ProcessingException("Store checking failed.")
        return transaction

    @staticmethod
    def capture_destination(transaction):
        return transaction

    @staticmethod
    def capture_source(transaction):
        store_api.withdraw(transaction)
        return transaction

    @staticmethod
    def void(transaction):
        return transaction
