import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from queue import Empty

from ai import AI_BLOCK, AIClient, has_ai
from bot import TwitchError
from config_schema import (Action, MessageAction, PollAction, RerollAction,
                           SoundAction, VipAddAction)
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


@dataclass
class ScheduledTask:
    """A bot action to run when its time comes (e.g. remove a timed VIP)."""
    due_ms: float
    user_id: str
    user_name: str
    label: str


def _as_list(value) -> list[str]:
    """A str-or-list config value as a list."""
    return [value] if isinstance(value, str) else list(value)


def pick_text(variants) -> str:
    """Random choice from a str-or-list value."""
    return random.choice(_as_list(variants)) if isinstance(
        variants, list) else variants


def _plain_fallback(variants) -> str | None:
    """First variant without AI blocks, or None if everything is AI."""
    plain = [t for t in _as_list(variants) if not has_ai(t)]
    return plain[0] if plain else None


class App:
    def __init__(self, config, bot, roulette, renderer, audio,
                 config_dir=None):
        self.bot = bot
        self.roulette = roulette
        self.renderer = renderer
        self.audio = audio
        self.outcomes = config.outcomes
        self._current: tuple | None = None
        self._pending_polls: list[PendingPoll] = []
        self._scheduled: list[ScheduledTask] = []
        self._animation_cache: dict[str, object] = {}
        self._config_dir = config_dir
        ai_cfg = getattr(config, "ai", None)
        self._ai_cfg = ai_cfg
        self.ai: AIClient | None = AIClient(ai_cfg) if ai_cfg else None
        self._ai_stripped = False

    def run(self):
        self.bot.start()
        running = True
        while running:
            running = self.renderer.poll_events()
            self._step()
        self.bot.stop()

    def _step(self):
        self._check_pending_polls()
        self._run_due_tasks()

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
        outcome = self.outcomes[plan.winner_name]
        action = outcome.action

        # AI messages are generated BEFORE the spin starts, so the reveal
        # and the chat message stay close together.
        needs_ai = (has_ai(outcome.message)
                    or (isinstance(action, MessageAction)
                        and has_ai(action.text)))
        resolved = None
        if needs_ai:
            resolved = self._resolve_ai(outcome, redemption)
            if resolved is None:
                self._refund_and_apologize(redemption, plan.winner_name)
                return
            if self.ai is not None and not self.ai.available:
                self._disable_ai_outcomes()

        self.renderer.start_spin(
            plan.sequence, plan.winner_index,
            animation=self._outcome_animation(outcome),
            effect=outcome.effect)
        self._current = (redemption, plan, rerolls, resolved)

    def _resolve_ai(self, outcome, redemption) -> tuple | None:
        """Resolve every AI block in the outcome's texts before the spin.

        Returns (outcome_message, action_text) with AI blocks replaced by
        real answers (None = not AI / absent), or None on total failure.
        A failure falls back to a plain variant of the same text when one
        exists; refund happens only when there is nothing to fall back to.
        """
        action = outcome.action
        msg = None
        if outcome.message is not None:
            text = pick_text(outcome.message)
            if has_ai(text):
                text = self._run_ai(text, redemption)
                if text is None:
                    text = _plain_fallback(outcome.message)
                    if text is None:
                        return None
                    log.warning("AI failed — using a plain message variant "
                                "for %s", redemption["user_name"])
            msg = self._substitute(text, redemption)

        act_text = None
        if isinstance(action, MessageAction) and has_ai(action.text):
            act_text = self._run_ai(pick_text(action.text), redemption)
            if act_text is None:
                act_text = _plain_fallback(action.text)
                if act_text is None:
                    return None
                log.warning("AI failed — using a plain action text for %s",
                            redemption["user_name"])
            act_text = self._substitute(act_text, redemption)
        return msg, act_text

    def _run_ai(self, text: str, redemption: dict) -> str | None:
        """Replace each {{ai: ...}} block with an answer (None on failure)."""
        while True:
            m = AI_BLOCK.search(text)
            if m is None:
                return text
            prompt = self._substitute(m.group(1), redemption)
            reply = self.ai.generate(prompt)
            if reply is None:
                return None
            text = text[:m.start()] + reply + text[m.end():]

    def _substitute(self, text: str, redemption: dict) -> str:
        """Replace {user}, {time}, {stream_title}, {stream_category}."""
        info = {"time": datetime.now().strftime("%H:%M"),
                "stream_title": "", "stream_category": ""}
        try:
            ch = self.bot.get_channel_info()
            info["stream_title"] = ch.get("title", "")
            info["stream_category"] = ch.get("category", "")
        except TwitchError as e:
            log.warning("channel info unavailable: %s", e)
        return (text.replace("{user}", redemption.get("user_name", ""))
                    .replace("{time}", info["time"])
                    .replace("{stream_title}", info["stream_title"])
                    .replace("{stream_category}", info["stream_category"]))

    def _refund_and_apologize(self, redemption: dict, outcome_name: str) \
            -> None:
        """The AI had to answer but couldn't: apology + points back."""
        log.warning("AI failed for %s — refunding %s", outcome_name,
                    redemption["user_name"])
        fallback = (self._ai_cfg.fallback_message if self._ai_cfg
                    else "The AI broke down entirely... {user}, your "
                         "points are back, the roulette is sorry!")
        try:
            self.bot.send_chat_message(
                self._substitute(fallback, redemption))
        except TwitchError as e:
            log.error("apology message failed: %s", e)
        try:
            self.bot.refund_redemption(redemption["id"])
            log.info("redemption %s refunded (%s)", redemption["id"],
                     redemption["user_name"])
        except TwitchError as e:
            log.error("refund failed for %s: %s", redemption["id"], e)
        self._disable_ai_outcomes()

    def _disable_ai_outcomes(self) -> None:
        """AI is dead for this session: strip AI variants; outcomes whose
        texts were AI-only can't be drawn anymore."""
        if getattr(self, "_ai_stripped", False):
            return
        self._ai_stripped = True
        disabled = []
        for name, o in self.outcomes.items():
            dropped = False
            if has_ai(o.message):
                kept = [t for t in _as_list(o.message) if not has_ai(t)]
                if kept:
                    o.message = kept
                    log.warning("outcome %s: AI message variants dropped",
                                name)
                else:
                    o.message = None
                    dropped = True
            if isinstance(o.action, MessageAction) and has_ai(o.action.text):
                kept = [t for t in _as_list(o.action.text) if not has_ai(t)]
                if kept:
                    o.action.text = kept
                    log.warning("outcome %s: AI action texts dropped", name)
                else:
                    dropped = True
            if dropped:
                disabled.append(name)
                log.warning("outcome %s disabled: it was AI-only", name)
        if disabled:
            self.roulette.exclude(disabled)

    def _outcome_animation(self, outcome):
        path = getattr(outcome, "animation", None)
        if not path or self._config_dir is None:
            return None
        key = str(path)
        if key not in self._animation_cache:
            from animations import load_animation
            self._animation_cache[key] = load_animation(
                self._config_dir / path,
                (self.renderer.width, self.renderer.height))
        return self._animation_cache[key]

    def _apply_consequence(self):
        if self._current is None:
            return
        redemption, plan, rerolls, resolved = self._current
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
        elif isinstance(action, VipAddAction) and action.duration:
            if apply(self.bot, action, redemption["user_id"],
                     redemption["user_name"]):
                self._schedule_remove_vip(action.duration, redemption)
        elif isinstance(action, MessageAction) and resolved is not None \
                and resolved[1] is not None:
            # AI-resolved action text (already generated before the spin).
            apply(self.bot, MessageAction(text=resolved[1]),
                  redemption["user_id"], redemption["user_name"])
        else:
            apply(self.bot, action, redemption["user_id"],
                  redemption["user_name"])

        if resolved is not None and resolved[0] is not None:
            # AI-resolved outcome message.
            apply(self.bot, MessageAction(text=resolved[0]),
                  redemption["user_id"], redemption["user_name"])
        elif resolved is None and outcome.message is not None:
            self._send_outcome_message(outcome, redemption)

        self._fulfill(redemption)
        self.audio.play(sound_path, sound_volume)
        log.info("%s -> %s (%s)", redemption["user_name"], plan.winner_name,
                 action.type)
        self._current = None

    def _send_outcome_message(self, outcome, redemption: dict) -> None:
        text = pick_text(outcome.message)
        text = self._substitute(text, redemption)
        apply(self.bot, MessageAction(text=text),
              redemption["user_id"], redemption["user_name"])

    def _fulfill(self, redemption: dict) -> None:
        try:
            self.bot.fulfill_redemption(redemption["id"])
        except TwitchError as e:
            log.error("fulfill failed for %s: %s", redemption["id"], e)

    def _schedule_remove_vip(self, seconds: int, redemption: dict) -> None:
        now = time.monotonic() * 1000
        self._scheduled.append(ScheduledTask(
            due_ms=now + seconds * 1000,
            user_id=redemption["user_id"],
            user_name=redemption["user_name"],
            label="timed vip",
        ))
        log.info("vip granted to %s for %d s", redemption["user_name"],
                 seconds)

    def _run_due_tasks(self) -> None:
        if not self._scheduled:
            return
        now = time.monotonic() * 1000
        for task in [t for t in self._scheduled if now >= t.due_ms]:
            self._scheduled.remove(task)
            try:
                self.bot.remove_vip(task.user_id)
                log.info("%s expired for %s — vip removed", task.label,
                         task.user_name)
            except TwitchError as e:
                log.error("failed to remove expired %s for %s: %s",
                          task.label, task.user_name, e)

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
