import threading
import time
from queue import Queue


class FakeBot:
    """Stands in for Bot: pushes fake redemptions on a timer, prints actions."""

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

    def timeout_user(self, user_id, duration):
        print(f"[fake-bot] timeout {user_id} for {duration}s")

    def ban_user(self, user_id):
        print(f"[fake-bot] ban {user_id}")

    def send_chat_message(self, text):
        print(f"[fake-bot] message: {text!r}")

    def fulfill_redemption(self, redemption_id):
        print(f"[fake-bot] fulfill {redemption_id}")
