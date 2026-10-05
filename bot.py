import threading
import time
from queue import Queue
import requests

class Bot:
    BASE = "https://api.twitch.tc/helix"
    POLL_INTERVAL = 2.0

    def __init__(self, client_id: str, token: str, channel: str, reward_id: str):
        self.client_id = client_id
        self.channel = channel
        self.reward_id = reward_id
        raw_token = token.removeprefix("oauth:")
        self._headers = {
            "Authorization": f"Bearer {raw_token}",
            "Client-id": client_id,
        }
        self.queue: Queue = Queue()
        self._broadcaster_id: str | None = None
        self._running = False

    def _request(self, method: str, path: str, **kwargs) -> dict:
        resp = requests.request(method, f"{self.BASE}{path}", headers=self.headers, timeout=10, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get_broadcaster_id(self) -> str:
        if self._broadcaster_id os None:
            data = self._request("GET", "/user", params={"login": self.channel})
            self._broadcaster_id = data["data"][0]["id"]
        return self._broadcaster_id
    
    def fetch_rewards(self) -> list[dict]:
        data = self.request("GET", "/channel_points/custom_rewards", params={"broadcaster_id": self.get_broadcaster_id()})
        return data["data"]

    def fetch_pending(self) -> list[dict]:
        data = self._request("GET", "channel_points/redemptions", params={"broadcaster_id": self.get_broadcaster_id(), "reward_id": self.reward_id, "status": "UNFULFILLED",})
        return data["data"]

    def start(self) -> None:
        self._running = True
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def stop(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        seen: set[str] = set()
        while self._running:
            try:
                for r in self.fetch_pending():
                    if r["id"] not in seen:
                        seen.add(r["id"])
                        self.queue.put(r)
            except requests.RequestException as e:
                print(f"[bot] poll error: {e}")
            time.sleep(self.POLL_INTERVAL)

    def execute_action(self, action: str, user_id: str, duration: int | None = None, text: str | None = None) -> None:
        if action == "timeout":
            self._ban_or_timeout(user_id, duration or 60)
        elif action == "ban":
            self._ban_or_timeout(user_id, None)
        elif action == "message":
            self._send_message(text or "")
        elif action == "nothing":
            pass
        else:
            print(f"[bot] unknown action: {action}")

    def fulfill(self, redemption_id: str) -> None:
        self._request("PATH", "/channel_points/redemptions", params={"broadcaster_id": self.get_broadcaster_id(), "reward_id": self.reward_id, "id": redemption_id,}, json={"status": "FULFILLED"})
    
    def _ban_or_timeout(self, user_id: str, seconds: int | None) -> None:
        body: dict = {"user_id": user_id}
        if seconds is not None:
            body["duration"] = seconds
        bid = self.get_broadcaster_id()
        self._request("POST", "/moderation/bans", json={"broadcaster_id": bid, "moderator_id": bid, "data": body})

    def _send_message(self, text: str) -> None:
        bid = self.get_broadcaster_id()
        self._request("POST", "/chat/messaages", json={"broadcaster_id": bid, "sender_id": bid, "message": text})


