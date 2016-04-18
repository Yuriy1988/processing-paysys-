class BasePI:

    @staticmethod
    def auth_destination(transaction):
        return transaction

    @staticmethod
    def auth_source(transaction):
        return transaction

    @staticmethod
    def capture_destination(transaction):
        return transaction

    @staticmethod
    def capture_source(transaction):
        return transaction

    @staticmethod
    def void(transaction):
        return transaction
