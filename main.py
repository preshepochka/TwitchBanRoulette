import logging

from app import App
from bot import Bot
from config_manager import ConfigManager
from renderer import Renderer
from roulette import Roulette


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    manager = ConfigManager("config.toml")
    if not manager.validate():
        raise SystemExit(1)
    cfg = manager.load()

    base = manager.config_path.parent
    card_paths = [base / o.image for o in cfg.outcomes.values()]
    overlay_path = (base / cfg.window.overlay) if cfg.window.overlay else None

    twitch = cfg.twitch
    bot = Bot(twitch.client_id, twitch.token, twitch.channel, twitch.reward_id)
    renderer = Renderer(cfg.window, card_paths, overlay_path)
    roulette = Roulette(cfg.outcomes, cfg.window)

    app = App(cfg, bot, roulette, renderer)
    app.run()


if __name__ == "__main__":
    main()
