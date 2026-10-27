import random
import threading
import time
from queue import Queue

from bot import TwitchError


class FakeBot:
    """Stands in for Bot: pushes fake redemptions on a timer, prints actions."""

    def __init__(self, every: float = 6.0):
        self.queue: Queue = Queue()
        self.every = every
        self._running = False
        self._n = 0
        self._poll_n = 0
        self._last_poll_choices: list[str] = []
        self.fail_polls = 0
        self.poll_active_rounds = 0

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

    def create_poll(self, title, choices, duration):
        self._poll_n += 1
        self._last_poll_choices = list(choices)
        print(f"[fake-bot] poll {duration}s: {title!r} choices={list(choices)}")
        return f"fake-poll-{self._poll_n}"

    def get_poll(self, poll_id):
        if self.fail_polls > 0:
            self.fail_polls -= 1
            raise TwitchError("fake poll fetch failure")
        status = "ACTIVE" if self.poll_active_rounds > 0 else "COMPLETED"
        if self.poll_active_rounds > 0:
            self.poll_active_rounds -= 1
        return {"status": status,
                "choices": [{"title": t, "votes": random.randint(1, 100)}
                            for t in self._last_poll_choices]}

    def add_vip(self, user_id):
        print(f"[fake-bot] vip+ {user_id}")

    def remove_vip(self, user_id):
        print(f"[fake-bot] vip- {user_id}")

    def fulfill_redemption(self, redemption_id):
        print(f"[fake-bot] fulfill {redemption_id}")
