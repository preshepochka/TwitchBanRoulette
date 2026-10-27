import logging
import math
import struct
import sys
import wave
from pathlib import Path

import pygame

from app import App
from audio import Audio
from bot import Bot
from config_manager import ConfigManager
from config_schema import (BanAction, Config, MessageAction, Outcome,
                           PollAction, RerollAction, SoundAction,
                           SoundConfig, TimeoutAction, VipAddAction,
                           WindowConfig)
from fake_bot import FakeBot
from renderer import Renderer, RenderEvent
from roulette import Roulette

log = logging.getLogger(__name__)

DEFAULT_WINDOW = (800, 200)

CARDS = {
    "timeout": (255, 140, 0),
    "ban":     (220, 0, 60),
    "message": (0, 140, 255),
    "reroll":  (170, 0, 255),
    "poll":    (0, 200, 140),
    "vip":     (255, 210, 0),
    "airhorn": (255, 0, 190),
}

SOUNDS = {
    "spin":    (441, 0.10),
    "tick":    (880, 0.03),
    "result":  (660, 0.35),
    "airhorn": (330, 0.40),
}


def app_root() -> Path:
    """Folder holding config.toml and assets/ (exe dir when frozen)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def config_path() -> Path:
    return app_root() / "config.toml"


def _load_config() -> tuple[ConfigManager, Config]:
    manager = ConfigManager(str(config_path()))
    if not manager.validate():
        raise SystemExit("invalid config")
    return manager, manager.load()


def run_demo() -> None:
    """Full pipeline with no config and no Twitch: FakeBot + Space."""
    assets = app_root() / "assets"
    if not assets.is_dir():
        raise SystemExit(
            f"assets folder not found: {assets}\n"
            "run with --placeholders to create it, or reinstall")
    overlay = assets / "overlay.png"
    window = WindowConfig(
        width=DEFAULT_WINDOW[0],
        height=DEFAULT_WINDOW[1],
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

    audio = Audio(app_root(), cfg.sounds)
    renderer = Renderer(window, [Path(o.image) for o in outcomes.values()],
                        overlay, audio=audio)
    roulette = Roulette(cfg.outcomes, cfg.window, cfg.roulette)
    print("Demo: auto-redemptions every 5s, Space — manual spin.")

    app = App(cfg, FakeBot(every=5.0), roulette, renderer, audio)
    app.run()


def run_renderer_test() -> None:
    """Window only: Space triggers a spin, outcomes come from config.toml."""
    manager, cfg = _load_config()
    audio = Audio(manager.config_path.parent, cfg.sounds)
    renderer = Renderer(cfg.window, manager.card_paths(),
                        manager.overlay_path(), manager.background_path(),
                        audio)
    roulette = Roulette(cfg.outcomes, cfg.window, cfg.roulette)
    print("Window started. Space — roll.")

    last_winner = None
    running = True
    while running:
        running = renderer.poll_events()
        if renderer.pop_debug_spin():
            plan = roulette.generate_spin()
            last_winner = plan.winner_name
            renderer.start_spin(plan.sequence, plan.winner_index)

        event = renderer.draw()
        if event is RenderEvent.SPIN_FINISHED:
            print(f"Result: {last_winner}")
        elif event is RenderEvent.RESULT_HIDDEN:
            print("Returned to idle.")


def run_app_test() -> None:
    """Full pipeline against FakeBot using the real config.toml."""
    manager, cfg = _load_config()
    audio = Audio(manager.config_path.parent, cfg.sounds)
    renderer = Renderer(cfg.window, manager.card_paths(),
                        manager.overlay_path(), manager.background_path(),
                        audio)
    roulette = Roulette(cfg.outcomes, cfg.window, cfg.roulette)
    app = App(cfg, FakeBot(every=6.0), roulette, renderer, audio)
    app.run()


def list_rewards() -> None:
    """Print channel-points reward IDs to fill twitch.reward_id."""
    manager, cfg = _load_config()
    if cfg.twitch is None:
        raise SystemExit("no [twitch] section in config.toml — "
                         "fill it in first (see README)")
    t = cfg.twitch
    bot = Bot(t.client_id, t.token, t.channel, t.reward_id)
    for r in bot.fetch_rewards():
        print(f'{r["id"]}  {r["title"]}')


def generate_placeholders(force: bool = False) -> None:
    """(Re)create placeholder assets next to the app. Existing files are
    kept unless force is set, so custom art is never clobbered by accident."""
    pygame.init()
    assets = app_root() / "assets"
    width, height = _window_size()
    targets = []
    for name, color in CARDS.items():
        targets.append((assets / "cards" / f"{name}.png",
                        lambda p, c=color: _make_card(p, c)))
    for name, (freq, secs) in SOUNDS.items():
        targets.append((assets / "sounds" / f"{name}.wav",
                        lambda p, f=freq, s=secs: _make_sound(p, f, s)))
    targets.append((assets / "overlay.png",
                    lambda p: _make_overlay(p, width, height)))

    made, skipped = 0, 0
    for path, maker in targets:
        if path.exists() and not force:
            skipped += 1
            log.info("skipped, exists (use --force to overwrite): %s", path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        maker(path)
        made += 1
    log.info("placeholders: %d created, %d skipped -> %s", made, skipped,
             assets)


def _window_size() -> tuple[int, int]:
    path = config_path()
    if path.exists():
        try:
            cfg = ConfigManager(str(path)).load()
            return cfg.window.width, cfg.window.height
        except Exception as e:
            log.warning("cannot read window size from %s (%s), "
                        "using %dx%d", path, e, *DEFAULT_WINDOW)
    return DEFAULT_WINDOW


def _make_card(path: Path, color: tuple) -> None:
    surf = pygame.Surface((150, 150), pygame.SRCALPHA)
    surf.fill((*color, 255))
    pygame.draw.rect(surf, (255, 255, 255), surf.get_rect(), 4)
    pygame.image.save(surf, str(path))


def _make_sound(path: Path, freq: int, seconds: float,
                volume: float = 0.4) -> None:
    rate = 44100
    n = int(rate * seconds)
    if rate % freq == 0:
        period = rate // freq
        n = max(period, n // period * period)
    frames = b"".join(
        struct.pack("<h", int(volume * 32767 * math.sin(2 * math.pi * freq * i / rate)))
        for i in range(n)
    )
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(frames)


def _make_overlay(path: Path, w: int, h: int) -> None:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = w // 2
    pygame.draw.polygon(surf, (255, 255, 255, 255),
                        [(cx - 20, 0), (cx + 20, 0), (cx, 38)])
    pygame.draw.rect(surf, (255, 255, 255, 200), surf.get_rect(), 4)
    pygame.image.save(surf, str(path))
