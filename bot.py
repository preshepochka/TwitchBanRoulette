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
    VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
    POLL_INTERVAL = 2.0
    TIMEOUT = 10
    # Scopes the core loop cannot work without.
    REQUIRED_SCOPES = {"channel:manage:redemptions",     # poll + fulfill
                       "moderator:manage:banned_users"}  # timeout/ban
    # Scope -> the feature that needs it (nice to have, warn only).
    OPTIONAL_SCOPES = {
        "channel:manage:polls": "poll action",
        "channel:manage:vips": "vip_add/vip_remove actions",
        "user:write:chat": "message action",
        "moderator:manage:announcements": "announce action",
    }

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
        self._channel_info: dict | None = None
        self._channel_info_at: float = 0.0
        self._running = False

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.BASE}{path}"
        try:
            resp = requests.request(method, url, headers=self._headers,
                                    timeout=self.TIMEOUT, **kwargs)
            resp.raise_for_status()
        except requests.RequestException as e:
            detail = ""
            resp_ = getattr(e, "response", None)
            if resp_ is not None:
                body = (resp_.text or "")[:300]
                if body:
                    detail = f" | body: {body}"
                if resp_.status_code == 401:
                    detail += ("\nHINT: the token is invalid or expired — "
                               "re-authorize using the link in README "
                               "('Getting a token') and update twitch.token.")
                elif resp_.status_code == 403:
                    low = (resp_.text or "").lower()
                    if "custom reward" in low and "client" in low:
                        detail += ("\nHINT: this reward was created in the "
                                   "Creator Dashboard, and Twitch only lets "
                                   "the creating client manage its "
                                   "redemptions. Create the reward through "
                                   "this app instead: run with --create-reward "
                                   "(see README).")
                    else:
                        detail += ("\nHINT: the token lacks the required "
                                   "scope — re-authorize using the link in "
                                   "README ('Getting a token'); copy the "
                                   "whole URL, it lists every scope the app "
                                   "needs.")
            raise TwitchError(f"{method} {url}: {e}{detail}") from e
        return resp.json()

    def _check_scopes(self) -> None:
        """Log a warning when the token lacks scopes the app needs."""
        try:
            resp = requests.get(
                self.VALIDATE_URL,
                headers={"Authorization":
                         f"OAuth {self._headers['Authorization'].removeprefix('Bearer ')}"},
                timeout=self.TIMEOUT)
            resp.raise_for_status()
            granted = set(resp.json().get("scopes") or [])
        except (requests.RequestException, ValueError) as e:
            log.warning("cannot validate token scopes: %s", e)
            return
        missing = self.REQUIRED_SCOPES - granted
        if missing:
            log.warning(
                "token is missing required scopes: %s — watching "
                "redemptions/fulfilling/timeout/ban will fail with 403. "
                "Re-authorize using the link in README (Getting a token).",
                ", ".join(sorted(missing)))
        optional_missing = sorted(
            f"{scope} ({feature})" for scope, feature in self.OPTIONAL_SCOPES.items()
            if scope not in granted)
        if optional_missing:
            log.info("token lacks optional scopes: %s — those actions "
                     "will log errors if used", ", ".join(optional_missing))

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

    def create_reward(self, title: str, cost: int,
                      prompt: str = "") -> str:
        """Create the reward with THIS app's client_id.

        Rewards created in the Creator Dashboard belong to the dashboard
        client, and Twitch refuses to let any other client read redemptions
        of such rewards (403) — so the reward must be created via the API.
        Requires the channel:manage:redemptions scope.
        """
        bid = self.get_broadcaster_id()
        body: dict = {"title": title, "cost": cost}
        if prompt:
            body["prompt"] = prompt
        data = self._request("POST", "/channel_points/custom_rewards",
                             params={"broadcaster_id": bid}, json=body)
        try:
            return data["data"][0]["id"]
        except (KeyError, IndexError, TypeError) as e:
            raise TwitchError(
                f"unexpected reward creation response: {data}") from e

    def fetch_pending(self) -> list[dict]:
        data = self._request("GET", "/channel_points/custom_rewards/redemptions",
                             params={"broadcaster_id": self.get_broadcaster_id(),
                                     "reward_id": self.reward_id,
                                     "status": "UNFULFILLED"})
        return data["data"]

    def start(self) -> None:
        self._check_scopes()
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

    def send_announcement(self, text: str, color: str = "primary") -> None:
        bid = self.get_broadcaster_id()
        self._request("POST", "/chat/announcements",
                      params={"broadcaster_id": bid, "moderator_id": bid},
                      json={"message": text, "color": color})

    def fulfill_redemption(self, redemption_id: str) -> None:
        self._request("PATCH", "/channel_points/custom_rewards/redemptions",
                      params={"broadcaster_id": self.get_broadcaster_id(),
                              "reward_id": self.reward_id,
                              "id": redemption_id},
                      json={"status": "FULFILLED"})

    def refund_redemption(self, redemption_id: str) -> None:
        """Cancel an UNFULFILLED redemption — Twitch returns the points."""
        self._request("PATCH", "/channel_points/custom_rewards/redemptions",
                      params={"broadcaster_id": self.get_broadcaster_id(),
                              "reward_id": self.reward_id,
                              "id": redemption_id},
                      json={"status": "CANCELED"})

    def get_channel_info(self) -> dict:
        """Stream title and category, cached for 5 minutes."""
        now = time.monotonic()
        if (self._channel_info is None
                or now - self._channel_info_at > 300):
            data = self._request("GET", "/channels",
                                 params={"broadcaster_id":
                                         self.get_broadcaster_id()})
            ch = data["data"][0]
            self._channel_info = {"title": ch.get("title") or "",
                                  "category": ch.get("game_name") or ""}
            self._channel_info_at = now
        return self._channel_info

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
        self._request("POST", "/channels/vips",
                      params={"broadcaster_id": self.get_broadcaster_id(),
                              "user_id": user_id})

    def remove_vip(self, user_id: str) -> None:
        self._request("DELETE", "/channels/vips",
                      params={"broadcaster_id": self.get_broadcaster_id(),
                              "user_id": user_id})

    def _ban_or_timeout(self, user_id: str, seconds: int | None) -> None:
        body: dict = {"user_id": user_id}
        if seconds is not None:
            body["duration"] = seconds
        bid = self.get_broadcaster_id()
        self._request("POST", "/moderation/bans",
                      params={"broadcaster_id": bid, "moderator_id": bid},
                      json={"data": body})
