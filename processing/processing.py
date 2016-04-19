from pi import process, ProcessingException
from processing.rabbitmq_connector import RabbitAsyncConsumer, RabbitPublisher
from tornado.queues import PriorityQueue


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
        while True:
            try:
                transaction = await self.queue.get()
                try:
                    transaction = await self.process(transaction)
                    await self.success(transaction)
                except ProcessingException as ex:
                    await self.fail(ex, transaction)
            except Exception as ex:
                await self.exception(ex, transaction)

    async def process(self, transaction):
        return transaction

    async def success(self, transaction):
        pass

    async def fail(self, error, transaction):
        pass

    async def exception(self, error, transaction):
        RabbitPublisher().put({"id": transaction["_id"], "status": "FAIL", "error": str(error)})


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
        super().__init__(RabbitAsyncConsumer(ioloop), step_name, ioloop, db, succeed_queue, fault_queue)

    async def process(self, transaction):
        transaction["_id"] = transaction.pop("id")  # change 'id' ot '_id'
        await self.db.transactions.insert(transaction)
        return transaction


class QueueStep(_InnerStep):
    def __init__(self, step_name, ioloop, db, succeed_queue, fault_queue, payment_interface):
        super().__init__(PriorityQueue(), step_name, ioloop, db, succeed_queue, fault_queue)
        self.payment_interface = payment_interface

    async def process(self, transaction):
        return self.payment_interface(transaction)


class _FinalStep(StepProcessor):
    def __init__(self, step_name, ioloop, db, succeed_queue, fault_queue, payment_interface):
        super().__init__(PriorityQueue(), step_name, ioloop, db, succeed_queue, fault_queue)
        self.rabbit = RabbitPublisher()

    async def fail(self, error, transaction):
        transaction["error"] = str(error)
        await update_transaction_status(self.db, transaction, PSM[self.step_name][STATE_ACTION.RESULT])
        self.rabbit.put({"id": transaction["_id"], "status": "FAIL", "error": transaction.get("error")})


class SuccessStep(_FinalStep):
    async def success(self, transaction):
        await update_transaction_status(self.db, transaction, PSM[self.step_name][STATE_ACTION.RESULT])
        self.rabbit.put({"id": transaction["_id"], "status": "OK"})


class FailStep(_FinalStep):
    async def success(self, transaction):
        await update_transaction_status(self.db, transaction, PSM[self.step_name][STATE_ACTION.RESULT])
        self.rabbit.put({"id": transaction["_id"], "status": "FAIL", "error": transaction.get("error")})


class Processing:
    """Takes care about processing flow. Flow determine by processing state machine."""

    def __init__(self, db):
        self.db = db
        self.handlers = {}

    def init(self, ioloop):
        """Generate queues, handlers and add callbacks to ioloop"""
        self._generate_status_handlers(ioloop)

    def _generate_status_handlers(self, ioloop):

        for status, state in PSM.items():
            self.handlers[status] = globals()[state[STATE_ACTION.PROCESSOR]](
                step_name=status,
                ioloop=ioloop,
                db=self.db,
                succeed_queue=None,
                fault_queue=None,
                payment_interface=self._pi_factory(status)
            )

        for status, handler in self.handlers.items():
            if isinstance(handler, (AcceptingStep, QueueStep)):
                handler.succeed_queue = self.handlers[PSM[status][STATE_ACTION.SUCCESS]].queue
                handler.fault_queue = self.handlers[PSM[status][STATE_ACTION.FAIL]].queue
            ioloop.add_callback(handler.loop)

    @staticmethod
    def _pi_factory(status):
        def payment_method(transaction):
            pi_name = transaction["source"]["paysys_contract"]["payment_interface"]
            return process(pi_name, status.lower(), transaction)
        return payment_method

