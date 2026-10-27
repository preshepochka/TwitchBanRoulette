import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import App
from audio import Audio
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

    audio = Audio(manager.config_path.parent, cfg.sounds)
    renderer = Renderer(cfg.window, manager.card_paths(),
                        manager.overlay_path(), manager.background_path(),
                        audio)
    roulette = Roulette(cfg.outcomes, cfg.window, cfg.roulette)
    app = App(cfg, FakeBot(every=6.0), roulette, renderer, audio)
    app.run()


if __name__ == "__main__":
    main()
