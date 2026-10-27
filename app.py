import logging
import time
from dataclasses import dataclass
from queue import Empty

from bot import TwitchError
from config_schema import Action, PollAction, RerollAction, SoundAction
from outcomes import apply
from renderer import RenderEvent, RenderState

log = logging.getLogger(__name__)

MAX_REROLL_CHAIN = 8
POLL_RETRY_MS = 2000
POLL_MAX_ATTEMPTS = 15


@dataclass
class PendingPoll:
    poll_id: str
    on_win: dict[str, Action]
    user_id: str
    user_name: str
    deadline_ms: float
    next_check_ms: float = 0.0
    attempts: int = 0


class App:
    def __init__(self, config, bot, roulette, renderer, audio):
        self.bot = bot
        self.roulette = roulette
        self.renderer = renderer
        self.audio = audio
        self.outcomes = config.outcomes
        self._current: tuple | None = None
        self._pending_polls: list[PendingPoll] = []

    def run(self):
        self.bot.start()
        running = True
        while running:
            running = self.renderer.poll_events()
            self._step()
        self.bot.stop()

    def _step(self):
        self._check_pending_polls()

        if self.renderer.state is RenderState.IDLE:
            self._try_start_spin()

        event = self.renderer.draw()
        if event is RenderEvent.SPIN_FINISHED and self._current:
            self._apply_consequence()

    def _try_start_spin(self):
        try:
            redemption = self.bot.queue.get_nowait()
        except Empty:
            return
        log.info("reward redeemed by %s — spinning...",
                 redemption.get("user_name"))
        self._start_spin(redemption, 0)

    def _start_spin(self, redemption: dict, rerolls: int) -> None:
        plan = self.roulette.generate_spin()
        self.renderer.start_spin(plan.sequence, plan.winner_index)
        self._current = (redemption, plan, rerolls)

    def _apply_consequence(self):
        if self._current is None:
            return
        redemption, plan, rerolls = self._current
        outcome = self.outcomes[plan.winner_name]
        action = outcome.action

        if isinstance(action, RerollAction) and rerolls < MAX_REROLL_CHAIN:
            self.audio.play(outcome.sound, outcome.sound_volume)
            log.info("%s -> %s (reroll #%d)", redemption["user_name"],
                     plan.winner_name, rerolls + 1)
            self._start_spin(redemption, rerolls + 1)
            return

        sound_path = outcome.sound or self.audio.sounds.result
        sound_volume = outcome.sound_volume
        if isinstance(action, RerollAction):
            log.info("%s -> %s (reroll chain limit reached)",
                     redemption["user_name"], plan.winner_name)
        elif isinstance(action, SoundAction):
            sound_path, sound_volume = action.sound, action.volume
        elif isinstance(action, PollAction):
            try:
                self._start_poll(action, redemption)
            except TwitchError as e:
                log.error("poll creation failed: %s", e)
        else:
            apply(self.bot, action, redemption["user_id"],
                  redemption["user_name"])

        self._fulfill(redemption)
        self.audio.play(sound_path, sound_volume)
        log.info("%s -> %s (%s)", redemption["user_name"], plan.winner_name,
                 action.type)
        self._current = None

    def _fulfill(self, redemption: dict) -> None:
        try:
            self.bot.fulfill_redemption(redemption["id"])
        except TwitchError as e:
            log.error("fulfill failed for %s: %s", redemption["id"], e)

    def _start_poll(self, action: PollAction, redemption: dict) -> None:
        poll_id = self.bot.create_poll(action.title, list(action.choices),
                                       action.duration)
        now = time.monotonic() * 1000
        self._pending_polls.append(PendingPoll(
            poll_id=poll_id,
            on_win=dict(action.on_win),
            user_id=redemption["user_id"],
            user_name=redemption["user_name"],
            deadline_ms=now + action.duration * 1000,
        ))
        log.info("poll started for %s (%d s): %s",
                 redemption["user_name"], action.duration, action.title)

    def _check_pending_polls(self) -> None:
        if not self._pending_polls:
            return
        now = time.monotonic() * 1000
        for p in list(self._pending_polls):
            if now < p.deadline_ms or now < p.next_check_ms:
                continue
            p.attempts += 1
            p.next_check_ms = now + POLL_RETRY_MS
            try:
                poll = self.bot.get_poll(p.poll_id)
            except TwitchError as e:
                if p.attempts >= POLL_MAX_ATTEMPTS:
                    log.error("giving up on poll %s results: %s", p.poll_id, e)
                    self._pending_polls.remove(p)
                else:
                    log.warning("poll %s result fetch failed: %s",
                                p.poll_id, e)
                continue

            status = poll.get("status")
            if status == "ACTIVE":
                continue
            self._pending_polls.remove(p)
            if status != "COMPLETED":
                log.error("poll %s ended with status %s, no action taken",
                          p.poll_id, status)
                continue
            choices = poll.get("choices") or []
            if not choices:
                log.error("poll %s finished with no choices", p.poll_id)
                continue
            winner = max(choices, key=lambda c: c.get("votes", 0))
            self._resolve_poll(p, winner.get("title", ""))

    def _resolve_poll(self, pending: PendingPoll, winner_title: str) -> None:
        log.info("poll result for %s: %r", pending.user_name, winner_title)
        action = pending.on_win.get(winner_title)
        if action is None:
            log.info("no action mapped for choice %r", winner_title)
            return
        if isinstance(action, RerollAction):
            log.warning("reroll is not supported as a poll result, skipped")
            return
        if isinstance(action, SoundAction):
            self.audio.play(action.sound, action.volume)
            return
        apply(self.bot, action, pending.user_id, pending.user_name)
