import logging

from app import App
from audio import Audio
from bot import Bot
from config_manager import ConfigManager
from config_schema import Config, LoggingConfig
from renderer import Renderer
from roulette import Roulette

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def _apply_logging_config(manager: ConfigManager, lc: LoggingConfig) -> None:
    """Reconfigure logging once the config is loaded.

    basicConfig above guarantees early errors (bad config) are visible;
    this applies the user's chosen level and adds the optional log file.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, lc.level.upper(), logging.INFO))
    if lc.file:
        handler = logging.FileHandler(
            manager.config_path.parent / lc.file, encoding="utf-8")
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(handler)


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    manager = ConfigManager("config.toml")
    if not manager.validate():
        raise SystemExit(1)
    cfg = manager.load()

    _apply_logging_config(manager, cfg.logging)

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
