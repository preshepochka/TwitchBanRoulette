import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import App
from audio import Audio
from config_schema import (BanAction, Config, MessageAction, Outcome,
                           PollAction, RerollAction, SoundAction,
                           SoundConfig, TimeoutAction, VipAddAction,
                           WindowConfig)
from fake_bot import FakeBot
from renderer import Renderer
from roulette import Roulette


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    base = Path(__file__).resolve().parent.parent
    assets = base / "assets"
    overlay = assets / "overlay.png"
    window = WindowConfig(
        width=800,
        height=200,
        chroma_key=(0, 255, 0),
        overlay=str(overlay),
    )
    sounds = SoundConfig(
        spin="assets/sounds/spin.wav",
        tick="assets/sounds/tick.wav",
        result="assets/sounds/result.wav",
    )
    outcomes = {
        "Timeout": Outcome(image=str(assets / "cards/timeout.png"), weight=25,
                           action=TimeoutAction(duration=60)),
        "Ban": Outcome(image=str(assets / "cards/ban.png"), weight=5,
                       action=BanAction()),
        "Message": Outcome(image=str(assets / "cards/message.png"), weight=20,
                           action=MessageAction(text="{user}, тебе повезло")),
        "Reroll": Outcome(image=str(assets / "cards/reroll.png"), weight=10,
                          sound="assets/sounds/tick.wav",
                          action=RerollAction()),
        "Poll": Outcome(image=str(assets / "cards/poll.png"), weight=15,
                        action=PollAction(title="Куда идём вечером?",
                                          choices=["Баня", "Мут"],
                                          duration=15,
                                          on_win={
                                              "Баня": TimeoutAction(duration=60),
                                              "Мут": MessageAction(
                                                  text="{user} избежал бани"),
                                          })),
        "Vip": Outcome(image=str(assets / "cards/vip.png"), weight=15,
                       action=VipAddAction()),
        "Airhorn": Outcome(image=str(assets / "cards/airhorn.png"), weight=10,
                           action=SoundAction(
                               sound="assets/sounds/airhorn.wav")),
    }
    cfg = Config(window=window, sounds=sounds, outcomes=outcomes)

    audio = Audio(base, cfg.sounds)
    renderer = Renderer(window, [Path(o.image) for o in outcomes.values()],
                        overlay, audio=audio)
    roulette = Roulette(cfg.outcomes, cfg.window, cfg.roulette)
    print("Demo: auto-redemptions every 5s, Space — manual spin.")

    app = App(cfg, FakeBot(every=5.0), roulette, renderer, audio)
    app.run()


if __name__ == "__main__":
    main()
