import logging
from pathlib import Path

from app import App
from config_schema import (BanAction, Config, MessageAction, Outcome,
                           PollAction, RerollAction, TimeoutAction,
                           VipAddAction, WindowConfig)
from fake_bot import FakeBot
from renderer import Renderer
from roulette import Roulette


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    assets = Path(__file__).resolve().parent.parent / "assets"
    window = WindowConfig(
        width=800,
        height=200,
        chroma_key=(0, 255, 0),
        overlay=str(assets / "overlay.png"),
    )
    outcomes = {
        "Timeout": Outcome(image=str(assets / "cards/timeout.png"), weight=30,
                           action=TimeoutAction(duration=60)),
        "Ban": Outcome(image=str(assets / "cards/ban.png"), weight=5,
                       action=BanAction()),
        "Message": Outcome(image=str(assets / "cards/message.png"), weight=25,
                           action=MessageAction(text="{user}, тебе повезло")),
        "Reroll": Outcome(image=str(assets / "cards/reroll.png"), weight=10,
                          action=RerollAction()),
        "Poll": Outcome(image=str(assets / "cards/poll.png"), weight=15,
                        action=PollAction(title="Куда идём вечером?",
                                          choices=["Баня", "Мут"],
                                          duration=60)),
        "Vip": Outcome(image=str(assets / "cards/vip.png"), weight=15,
                       action=VipAddAction()),
    }
    cfg = Config(window=window, outcomes=outcomes)

    renderer = Renderer(window, [Path(o.image) for o in outcomes.values()],
                        Path(window.overlay))
    roulette = Roulette(cfg.outcomes, cfg.window, cfg.roulette)
    print("Demo: auto-redemptions every 5s, Space — manual spin.")

    app = App(cfg, FakeBot(every=5.0), roulette, renderer)
    app.run()


if __name__ == "__main__":
    main()
