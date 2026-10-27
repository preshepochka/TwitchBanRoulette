import logging
import threading
import time
from queue import Queue

import requests

log = logging.getLogger(__name__)


class TwitchError(RuntimeError):
    """A Twitch API request failed."""


class Bot:
    """Twitch transport: Helix requests, redemption polling, action calls."""

    BASE = "https://api.twitch.tv/helix"
    POLL_INTERVAL = 2.0
    TIMEOUT = 10

    def __init__(self, client_id: str, token: str, channel: str, reward_id: str):
        self.channel = channel
        self.reward_id = reward_id
        raw_token = token.removeprefix("oauth:")
        self._headers = {
            "Authorization": f"Bearer {raw_token}",
            "Client-Id": client_id,
        }
        self.queue: Queue = Queue()
        self._broadcaster_id: str | None = None
        self._running = False

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.BASE}{path}"
        try:
            resp = requests.request(method, url, headers=self._headers,
                                    timeout=self.TIMEOUT, **kwargs)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise TwitchError(f"{method} {url}: {e}") from e
        return resp.json()

    def get_broadcaster_id(self) -> str:
        if self._broadcaster_id is None:
            data = self._request("GET", "/users", params={"login": self.channel})
            users = data.get("data") or []
            broadcaster_id = str(users[0].get("id") or "") if users else ""
            if not broadcaster_id:
                raise TwitchError(f"channel not found: {self.channel!r}")
            self._broadcaster_id = broadcaster_id
        return self._broadcaster_id

    def fetch_rewards(self) -> list[dict]:
        data = self._request("GET", "/channel_points/custom_rewards",
                             params={"broadcaster_id": self.get_broadcaster_id()})
        return data["data"]

    def fetch_pending(self) -> list[dict]:
        data = self._request("GET", "/channel_points/redemptions",
                             params={"broadcaster_id": self.get_broadcaster_id(),
                                     "reward_id": self.reward_id,
                                     "status": "UNFULFILLED"})
        return data["data"]

    def start(self) -> None:
        self.get_broadcaster_id()
        self._running = True
        threading.Thread(target=self._poll_loop, daemon=True,
                         name="twitch-poll").start()

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
            except TwitchError as e:
                log.warning("poll error: %s", e)
            time.sleep(self.POLL_INTERVAL)

    def timeout_user(self, user_id: str, duration: int) -> None:
        self._ban_or_timeout(user_id, duration)

    def ban_user(self, user_id: str) -> None:
        self._ban_or_timeout(user_id, None)

    def send_chat_message(self, text: str) -> None:
        bid = self.get_broadcaster_id()
        self._request("POST", "/chat/messages",
                      json={"broadcaster_id": bid, "sender_id": bid,
                            "message": text})

    def fulfill_redemption(self, redemption_id: str) -> None:
        self._request("PATCH", "/channel_points/redemptions",
                      params={"broadcaster_id": self.get_broadcaster_id(),
                              "reward_id": self.reward_id,
                              "id": redemption_id},
                      json={"status": "FULFILLED"})

    def create_poll(self, title: str, choices: list[str], duration: int) -> str:
        bid = self.get_broadcaster_id()
        data = self._request("POST", "/polls",
                             json={"broadcaster_id": bid,
                                   "title": title,
                                   "choices": [{"title": c} for c in choices],
                                   "duration": duration})
        try:
            return data["data"][0]["id"]
        except (KeyError, IndexError, TypeError) as e:
            raise TwitchError(f"unexpected poll creation response: {data}") from e

    def get_poll(self, poll_id: str) -> dict:
        data = self._request("GET", "/polls",
                             params={"broadcaster_id": self.get_broadcaster_id(),
                                     "id": poll_id})
        polls = data.get("data") or []
        return polls[0] if polls else {}

    def add_vip(self, user_id: str) -> None:
        self._request("POST", "/moderation/vips",
                      params={"broadcaster_id": self.get_broadcaster_id(),
                              "user_id": user_id})

    def remove_vip(self, user_id: str) -> None:
        self._request("DELETE", "/moderation/vips",
                      params={"broadcaster_id": self.get_broadcaster_id(),
                              "user_id": user_id})

    def _ban_or_timeout(self, user_id: str, seconds: int | None) -> None:
        body: dict = {"user_id": user_id}
        if seconds is not None:
            body["duration"] = seconds
        bid = self.get_broadcaster_id()
        self._request("POST", "/moderation/bans",
                      json={"broadcaster_id": bid, "moderator_id": bid,
                            "data": body})
