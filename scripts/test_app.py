import logging

from app import App
from config_manager import ConfigManager
from fake_bot import FakeBot
from renderer import Renderer
from roulette import Roulette


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    manager = ConfigManager("config.toml")
    if not manager.validate():
        raise SystemExit("invalid config")
    cfg = manager.load()

    renderer = Renderer(cfg.window, manager.card_paths(),
                        manager.overlay_path(), manager.background_path())
    roulette = Roulette(cfg.outcomes, cfg.window, cfg.roulette)
    app = App(cfg, FakeBot(every=6.0), roulette, renderer)
    app.run()


if __name__ == "__main__":
    main()
