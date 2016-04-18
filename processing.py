from pi import process
from rabbitmq_connector import RabbitAsyncConsumer, RabbitPublisher
from tornado.queues import PriorityQueue


class QUEUES:
    """Name for queues and statuses"""
    CAPTURE_SOURCE = "CAPTURE_SOURCE"
    CAPTURE_DESTINATION = "CAPTURE_DESTINATION"
    AUTH_SOURCE = "AUTH_SOURCE"
    AUTH_DESTINATION = "AUTH_DESTINATION"
    VOID = "VOID"


class STATUS(QUEUES):
    """Statuses for transactions"""
    ACCEPTED = "ACCEPTED"

    SUCCESS = "SUCCESS"
    FAIL = "FAIL"


class STATE_ACTION:
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    PROCESSOR = "PROCESSOR"


class StepProcessor:

    def __init__(self, queue):
        self.queue = queue
        self.transaction = None

    async def loop(self):
        while True:
            self.transaction = await self.queue.get()
            try:
                self.process()
                self.success()
            except Exception as ex:
                self.fail(ex)

    def process(self):
        pass

    def success(self):
        pass

    def fail(self, error):
        pass


class AcceptingStep(StepProcessor):

    def __init__(self, ioloop, db, succeed_queue, fault_queue, payment_interface):
        super().__init__(RabbitAsyncConsumer(ioloop))
        self.db = db
        self.succeed_queue = succeed_queue

    def process(self):
        self.transaction = self.transaction  # FIXME: Add decryption

    def success(self):
        self.succeed_queue.put(self.transaction)

    def fail(self, error):
        self.queue.put(error)


class QueueStep(StepProcessor):
    def __init__(self, ioloop, db, succeed_queue, fault_queue, payment_interface):
        super().__init__(PriorityQueue())
        self.db = db
        self.succeed_queue = succeed_queue
        self.fault_queue = fault_queue
        self.payment_interface = payment_interface

    def process(self):
        self.transaction = self.payment_interface(self.transaction)

    def success(self):
        self.succeed_queue.put(self.transaction)

    def fail(self, error):
        self.fault_queue.put(self.transaction)


class FinalStep(StepProcessor):

    def __init__(self, ioloop, db, succeed_queue, fault_queue, payment_interface):
        super().__init__(PriorityQueue())
        self.rabbit = RabbitPublisher()

    def success(self):
        self.rabbit.put({"Status": "OK"})

    def fail(self, error):
        self.rabbit.put(error)


class Processing:
    """Takes care about processing flow. Flow determine by processing state machine."""

    def __init__(self, db):
        self.db = db
        self.handlers = {}

    # psm == Processing state machine
    PSM = {
        STATUS.ACCEPTED: {
            STATE_ACTION.SUCCESS: STATUS.AUTH_SOURCE,
            STATE_ACTION.FAIL: STATUS.FAIL,
            STATE_ACTION.PROCESSOR: AcceptingStep,
        },
        STATUS.AUTH_SOURCE: {
            STATE_ACTION.SUCCESS: STATUS.AUTH_DESTINATION,
            STATE_ACTION.FAIL: STATUS.VOID,
            STATE_ACTION.PROCESSOR: QueueStep,
        },
        STATUS.AUTH_DESTINATION: {
            STATE_ACTION.SUCCESS: STATUS.CAPTURE_SOURCE,
            STATE_ACTION.FAIL: STATUS.VOID,
            STATE_ACTION.PROCESSOR: QueueStep,
        },
        STATUS.CAPTURE_SOURCE: {
            STATE_ACTION.SUCCESS: STATUS.CAPTURE_DESTINATION,
            STATE_ACTION.FAIL: STATUS.VOID,
            STATE_ACTION.PROCESSOR: QueueStep,
        },
        STATUS.CAPTURE_DESTINATION: {
            STATE_ACTION.SUCCESS: STATUS.SUCCESS,
            STATE_ACTION.FAIL: STATUS.VOID,
            STATE_ACTION.PROCESSOR: QueueStep,
        },
        STATUS.VOID: {
            STATE_ACTION.SUCCESS: STATUS.FAIL,
            STATE_ACTION.FAIL: STATUS.FAIL,
            STATE_ACTION.PROCESSOR: QueueStep,
        },
        STATUS.SUCCESS: {
            STATE_ACTION.PROCESSOR: FinalStep,
        },
        STATUS.FAIL: {
            STATE_ACTION.PROCESSOR: FinalStep,
        }
    }

    def init(self, ioloop):
        """Generate queues, handlers and add callbacks to ioloop"""
        self._generate_status_handlers(ioloop)

    def _generate_status_handlers(self, ioloop):

        for status, state in self.PSM.items():
            self.handlers[status] = state[STATE_ACTION.PROCESSOR](
                ioloop=ioloop,
                db=self.db,
                succeed_queue=None,
                fault_queue=None,
                payment_interface=self._pi_factory(status)
            )

        for status, handler in self.handlers.items():
            if isinstance(handler, (AcceptingStep, QueueStep)):
                handler.succeed_queue = self.handlers[self.PSM[status][STATE_ACTION.SUCCESS]].queue
                handler.fault_queue = self.handlers[self.PSM[status][STATE_ACTION.FAIL]].queue
            ioloop.add_callback(handler.loop)

    @staticmethod
    def _pi_factory(status):
        def payment_method(transaction):
            pi_name = transaction["source"]["paysys_contract"]["payment_interface"]
            return process(pi_name, status.lower(), transaction)
        return payment_method


if __name__ == '__main__':
    from tornado.ioloop import IOLoop
    p = Processing(db=None)
    p.init(ioloop=IOLoop.current())
    IOLoop.current().start()
