import threading
import time
from queue import Queue

class FakeBot:
    def __init__(self, every: float = 6.0):
        self.queue: Queue = Queue()
        self.every = every
        self._running = False
        self._n = 0

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            self._n += 1
            self.queue.put({
                "id": f"fake-{self._n}",
                "user_id": f"user-{self._n}",
                "user_name": f"FakeViewer{self._n}",
            })
            time.sleep(self.every)

    def execute_action(self, action, user_id, duration=None, text=None):
        print(f"[fake-bot] {action} -> {user_id} (duration={duration}, text={text!r})")

    def fulfill(self, redemption_id):
        print(f"[fake-bot] fulfill {redemption_id}")

