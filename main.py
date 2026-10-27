import logging

from app import App
from audio import Audio
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

    if cfg.twitch is None:
        logging.getLogger(__name__).error(
            "[twitch] section is required to run the real bot; "
            "for local testing use scripts/demo.py")
        raise SystemExit(1)

    twitch = cfg.twitch
    bot = Bot(twitch.client_id, twitch.token, twitch.channel, twitch.reward_id)
    audio = Audio(manager.config_path.parent, cfg.sounds)
    renderer = Renderer(cfg.window, manager.card_paths(),
                        manager.overlay_path(), manager.background_path(),
                        audio)
    roulette = Roulette(cfg.outcomes, cfg.window, cfg.roulette)

    app = App(cfg, bot, roulette, renderer, audio)
    app.run()


if __name__ == "__main__":
    main()
