import argparse
import logging
import sys

import pygame

from app import App
from audio import Audio
from bot import Bot
from config_manager import ConfigManager
from config_schema import LoggingConfig
from modes import (config_path, generate_placeholders, list_rewards,
                   run_app_test, run_demo, run_renderer_test)
from renderer import Renderer
from roulette import Roulette

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
log = logging.getLogger(__name__)


def _fatal_pause() -> None:
    """Keep the console open so double-clicked launches stay readable."""
    try:
        input("Press Enter to exit...")
    except (EOFError, KeyboardInterrupt):
        pass


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


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="TwitchBanRoulette",
        description="Channel-points roulette for Twitch streams.")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--demo", action="store_true",
                       help="demo mode: fake bot, no config or Twitch needed")
    modes.add_argument("--renderer", action="store_true",
                       help="window only: Space spins, outcomes from config")
    modes.add_argument("--test", action="store_true",
                       help="full pipeline with the fake bot on config.toml")
    modes.add_argument("--placeholders", action="store_true",
                       help="(re)create placeholder assets")
    modes.add_argument("--list-rewards", action="store_true",
                       help="print channel-points reward IDs")
    parser.add_argument("--force", action="store_true",
                        help="with --placeholders: overwrite existing files")
    args = parser.parse_args(argv)
    if args.force and not args.placeholders:
        parser.error("--force is only used together with --placeholders")
    return args


def _run_bot() -> None:
    manager = ConfigManager(str(config_path()))
    if not manager.validate():
        raise SystemExit(1)
    cfg = manager.load()

    _apply_logging_config(manager, cfg.logging)

    if cfg.twitch is None:
        log.error("[twitch] section is required to run the real bot; "
                  "for local testing use --demo")
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


def main(argv=None):
    args = _parse_args(argv)
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    log.info("starting TwitchBanRoulette (python %s, pygame %s%s)",
             sys.version.split()[0], pygame.version.ver,
             ", portable build" if getattr(sys, "frozen", False) else "")

    if args.demo:
        run_demo()
    elif args.renderer:
        run_renderer_test()
    elif args.test:
        run_app_test()
    elif args.placeholders:
        generate_placeholders(force=args.force)
    elif args.list_rewards:
        list_rewards()
    else:
        _run_bot()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (0, None):
            _fatal_pause()
        raise
    except KeyboardInterrupt:
        pass
    except Exception:
        log.exception("fatal error")
        _fatal_pause()
        raise SystemExit(1) from None
