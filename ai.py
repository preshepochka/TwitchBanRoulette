import logging
import re

import requests

from bot import TwitchError
from config_schema import AIConfig

log = logging.getLogger(__name__)

# {{ai: ...}} blocks in message texts; non-greedy so one text can hold
# several blocks.
AI_BLOCK = re.compile(r"\{\{ai:(.*?)\}\}", re.DOTALL)


def has_ai(text) -> bool:
    """Whether a str-or-list message value contains any {{ai: ...}} block."""
    if text is None:
        return False
    texts = [text] if isinstance(text, str) else text
    return any(AI_BLOCK.search(t) for t in texts)


class AIClient:
    """Generates chat text through an OpenAI-compatible API.

    Sources (base_url + api_key pairs) roll: the client starts with pair 0
    and advances to the next pair whenever the current one fails. Once every
    pair has failed, `available` goes False permanently — the app then
    removes AI variants from the roulette. Recovery is by restarting the app.
    """

    def __init__(self, cfg: AIConfig):
        self._cfg = cfg
        self._pairs = list(zip(cfg.base_urls, cfg.api_keys))
        self._index = 0
        self.available = True

    def generate(self, prompt: str) -> str | None:
        """One AI answer, or None when all sources failed."""
        if not self.available:
            return None
        for _ in range(len(self._pairs)):
            base_url, key = self._pairs[self._index]
            try:
                reply = self._ask(base_url, key, prompt)
                self.available = True
                return reply
            except (requests.RequestException, TwitchError, KeyError,
                    IndexError) as e:
                log.warning("AI source %s failed: %s", base_url, e)
                self._index = (self._index + 1) % len(self._pairs)
        log.error("no AI source answered — AI messages are disabled "
                  "until the app restarts")
        self.available = False
        return None

    def _ask(self, base_url: str, key: str, prompt: str) -> str:
        url = base_url.rstrip("/") + "/chat/completions"
        messages = []
        if self._cfg.system_prompt:
            messages.append({"role": "system",
                             "content": self._cfg.system_prompt})
        messages.append({"role": "user", "content": prompt})
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"model": self._cfg.model,
                  "messages": messages,
                  "temperature": self._cfg.temperature,
                  "max_tokens": self._cfg.max_tokens},
            timeout=self._cfg.timeout,
        )
        if resp.status_code != 200:
            raise TwitchError(f"HTTP {resp.status_code}: "
                              f"{resp.text[:300]}")
        content = resp.json()["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise TwitchError("empty AI reply")
        return content.strip()
