from store_api import BaseAPI


class TestAPI(BaseAPI):

    @staticmethod
    def check(transaction):
        return True

    @staticmethod
    def withdraw(transaction):
        return True
