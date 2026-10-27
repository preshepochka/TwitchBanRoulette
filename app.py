import logging
from queue import Empty

from bot import TwitchError
from config_schema import RerollAction
from outcomes import apply
from renderer import RenderEvent, RenderState

log = logging.getLogger(__name__)

MAX_REROLL_CHAIN = 8


class App:
    def __init__(self, config, bot, roulette, renderer):
        self.bot = bot
        self.roulette = roulette
        self.renderer = renderer
        self.outcomes = config.outcomes
        self._current = None

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
        self._start_spin(redemption, 0)

    def _start_spin(self, redemption: dict, rerolls: int) -> None:
        plan = self.roulette.generate_spin()
        self.renderer.start_spin(plan.sequence, plan.winner_index)
        self._current = (redemption, plan, rerolls)

    def _apply_consequence(self):
        redemption, plan, rerolls = self._current
        outcome = self.outcomes[plan.winner_name]

        if isinstance(outcome.action, RerollAction) and rerolls < MAX_REROLL_CHAIN:
            log.info("%s -> %s (reroll #%d)", redemption["user_name"],
                     plan.winner_name, rerolls + 1)
            self._start_spin(redemption, rerolls + 1)
            return

        ok = apply(self.bot, outcome.action, redemption["user_id"],
                   redemption["user_name"])
        if ok:
            try:
                self.bot.fulfill_redemption(redemption["id"])
            except TwitchError as e:
                log.error("fulfill failed for %s: %s", redemption["id"], e)
        log.info("%s -> %s (%s)", redemption["user_name"], plan.winner_name,
                 outcome.action.type)
        self._current = None
