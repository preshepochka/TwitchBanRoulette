import logging
from queue import Empty

from bot import TwitchError
from config_schema import RerollAction, SoundAction
from outcomes import apply
from renderer import RenderEvent, RenderState

log = logging.getLogger(__name__)

MAX_REROLL_CHAIN = 8


class App:
    def __init__(self, config, bot, roulette, renderer, audio):
        self.bot = bot
        self.roulette = roulette
        self.renderer = renderer
        self.audio = audio
        self.outcomes = config.outcomes
        self._current: tuple | None = None

    def run(self):
        self.bot.start()
        running = True
        while running:
            running = self.renderer.poll_events()
            self._step()
        self.bot.stop()

    def _step(self):
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

        if isinstance(action, SoundAction):
            ok = True
            sound_path, sound_volume = action.sound, action.volume
        else:
            ok = apply(self.bot, action, redemption["user_id"],
                       redemption["user_name"])
            sound_path = outcome.sound or self.audio.sounds.result
            sound_volume = outcome.sound_volume

        if ok:
            try:
                self.bot.fulfill_redemption(redemption["id"])
            except TwitchError as e:
                log.error("fulfill failed for %s: %s", redemption["id"], e)
        self.audio.play(sound_path, sound_volume)
        log.info("%s -> %s (%s)", redemption["user_name"], plan.winner_name,
                 action.type)
        self._current = None
