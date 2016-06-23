import logging
import asyncio
from asyncio.queues import PriorityQueue, Queue
from pymongo.errors import AutoReconnect

from queue_connect import RabbitPublisher
from paysys_pi import process, ProcessingException
from config import config


_log = logging.getLogger('xop.processing')


TRANSACTION_STATUS_ENUM = ('3D_SECURE', 'PROCESSED', 'SUCCESS', 'REJECTED')


class STATUS:
    """Statuses for transactions"""
    ACCEPTED = "ACCEPTED"

    CAPTURE_SOURCE = "CAPTURE_SOURCE"
    CAPTURE_DESTINATION = "CAPTURE_DESTINATION"
    AUTH_SOURCE = "AUTH_SOURCE"
    AUTH_DESTINATION = "AUTH_DESTINATION"
    VOID = "VOID"

    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


class STATE_ACTION:
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    PROCESSOR = "PROCESSOR"
    RESULT = "RESULT"

async def update_transaction_status(db, transaction, new_status):
    transaction['status'] = new_status
    return await db.transactions.update({'_id': transaction['_id']}, transaction)


# psm == Processing state machine
PSM = {
    STATUS.ACCEPTED: {
        STATE_ACTION.SUCCESS: STATUS.AUTH_SOURCE,
        STATE_ACTION.FAIL: STATUS.FAIL,
        STATE_ACTION.PROCESSOR: "AcceptingStep",
    },
    STATUS.AUTH_SOURCE: {
        STATE_ACTION.SUCCESS: STATUS.AUTH_DESTINATION,
        STATE_ACTION.FAIL: STATUS.VOID,
        STATE_ACTION.PROCESSOR: "QueueStep",
    },
    STATUS.AUTH_DESTINATION: {
        STATE_ACTION.SUCCESS: STATUS.CAPTURE_SOURCE,
        STATE_ACTION.FAIL: STATUS.VOID,
        STATE_ACTION.PROCESSOR: "QueueStep",
    },
    STATUS.CAPTURE_SOURCE: {
        STATE_ACTION.SUCCESS: STATUS.CAPTURE_DESTINATION,
        STATE_ACTION.FAIL: STATUS.VOID,
        STATE_ACTION.PROCESSOR: "QueueStep",
    },
    STATUS.CAPTURE_DESTINATION: {
        STATE_ACTION.SUCCESS: STATUS.SUCCESS,
        STATE_ACTION.FAIL: STATUS.VOID,
        STATE_ACTION.PROCESSOR: "QueueStep",
    },
    STATUS.VOID: {
        STATE_ACTION.SUCCESS: STATUS.FAIL,
        STATE_ACTION.FAIL: STATUS.FAIL,
        STATE_ACTION.PROCESSOR: "QueueStep",
    },
    STATUS.SUCCESS: {
        STATE_ACTION.RESULT: STATUS.SUCCESS,
        STATE_ACTION.PROCESSOR: "SuccessStep",
    },
    STATUS.FAIL: {
        STATE_ACTION.RESULT: STATUS.FAIL,
        STATE_ACTION.PROCESSOR: "FailStep",
    }
}

_transactions_incoming_queue = Queue()


async def handle_transaction(message):
    await _transactions_incoming_queue.put(message)


class StepProcessor:

    def __init__(self, queue, step_name, ioloop, db, succeed_queue, fault_queue):
        self.queue = queue
        self.step_name = step_name
        self.ioloop = ioloop
        self.db = db
        self.succeed_queue = succeed_queue
        self.fault_queue = fault_queue

    async def loop(self):
        transaction = None
        _log.info("Start main loop for " + self.step_name)
        while True:
            try:
                transaction = await self.queue.get()
                try:
                    transaction = await self.process(transaction)
                    await self.success(transaction)
                    _log.info("Successfully processed: " + self.step_name)
                except ProcessingException as ex:
                    _log.error("Processing error: " + str(ex))
                    await self.fail(ex, transaction)
            except AutoReconnect as ex:
                _log.error("Processing DB error: " + str(ex))
                await self.exception("MongoDB (AutoReconnect): " + str(ex), transaction)
            except Exception as ex:
                _log.error("Processing fatal failure: " + str(ex))
                await self.exception(ex, transaction)

    def stop(self):
        self.close()

    def close(self):
        pass

    async def process(self, transaction):
        return transaction

    async def success(self, transaction):
        pass

    async def fail(self, error, transaction):
        pass

    async def exception(self, error, transaction):
        RabbitPublisher(config['QUEUE_TRANS_STATUS']).put({"id": transaction["_id"], "status": "REJECTED", "error": str(error)})


class _InnerStep(StepProcessor):
    async def success(self, transaction):
        await update_transaction_status(self.db, transaction, PSM[self.step_name][STATE_ACTION.SUCCESS])
        self.succeed_queue.put(transaction)

    async def fail(self, error, transaction):
        transaction["error"] = str(error)
        await update_transaction_status(self.db, transaction, PSM[self.step_name][STATE_ACTION.FAIL])
        self.fault_queue.put(transaction)


class AcceptingStep(_InnerStep):
    def __init__(self, step_name, ioloop, db, succeed_queue, fault_queue, payment_interface):
        super().__init__(_transactions_incoming_queue, step_name, ioloop, db, succeed_queue, fault_queue)

    async def process(self, transaction):
        transaction["_id"] = transaction.pop("id")  # change 'id' ot '_id'
        await self.db.transactions.insert(transaction)
        return transaction

    def close(self):
        self.queue.close_connection()


class QueueStep(_InnerStep):
    def __init__(self, step_name, ioloop, db, succeed_queue, fault_queue, payment_interface):
        super().__init__(PriorityQueue(), step_name, ioloop, db, succeed_queue, fault_queue)
        self.payment_interface = payment_interface

    async def process(self, transaction):
        return self.payment_interface(transaction)


class _FinalStep(StepProcessor):
    def __init__(self, step_name, ioloop, db, succeed_queue, fault_queue, payment_interface):
        super().__init__(PriorityQueue(), step_name, ioloop, db, succeed_queue, fault_queue)
        self.rabbit = RabbitPublisher(config['QUEUE_TRANS_STATUS'])

    async def fail(self, error, transaction):
        transaction["error"] = str(error)
        await update_transaction_status(self.db, transaction, PSM[self.step_name][STATE_ACTION.RESULT])
        self.rabbit.put({"id": transaction["_id"], "status": "REJECTED", "error": transaction.get("error")})


class SuccessStep(_FinalStep):
    async def success(self, transaction):
        await update_transaction_status(self.db, transaction, PSM[self.step_name][STATE_ACTION.RESULT])
        self.rabbit.put({"id": transaction["_id"], "status": "SUCCESS"})


class FailStep(_FinalStep):
    async def success(self, transaction):
        await update_transaction_status(self.db, transaction, PSM[self.step_name][STATE_ACTION.RESULT])
        self.rabbit.put({"id": transaction["_id"], "status": "REJECTED", "error": transaction.get("error")})


class Processing:
    """Takes care about processing flow. Flow determine by processing state machine."""

    def __init__(self, db, loop=None):
        self.db = db
        self._loop = loop or asyncio.get_event_loop()

        self.handlers = {}

    def init(self):
        """Generate queues, handlers and add callbacks to ioloop"""
        self._generate_status_handlers()
        _log.info("Processing initialized")

    def _generate_status_handlers(self):

        for status, state in PSM.items():
            self.handlers[status] = globals()[state[STATE_ACTION.PROCESSOR]](
                step_name=status,
                ioloop=self._loop,
                db=self.db,
                succeed_queue=None,
                fault_queue=None,
                payment_interface=self._pi_factory(status)
            )

        for status, handler in self.handlers.items():
            if isinstance(handler, (AcceptingStep, QueueStep)):
                handler.succeed_queue = self.handlers[PSM[status][STATE_ACTION.SUCCESS]].queue
                handler.fault_queue = self.handlers[PSM[status][STATE_ACTION.FAIL]].queue
            asyncio.ensure_future(handler.loop())

    async def stop(self):
        for handler in self.handlers.values():
            handler.close()

    @staticmethod
    def _pi_factory(status):
        def payment_method(transaction):
            pi_name = transaction["source"]["paysys_contract"]["payment_interface"]
            return process(pi_name, status.lower(), transaction)
        return payment_method
