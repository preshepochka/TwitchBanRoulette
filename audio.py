import logging
from pathlib import Path

import pygame

from config_schema import SoundConfig

log = logging.getLogger(__name__)


class Audio:
    """Sound playback. Degrades to no-ops if the mixer is unavailable."""

    def __init__(self, base_dir: Path, sounds: SoundConfig):
        self.sounds = sounds
        self._base = base_dir
        self._master = sounds.volume
        self._cache: dict[str, pygame.mixer.Sound | None] = {}
        self._loop_channel: pygame.mixer.Channel | None = None
        self._ok = False
        if sounds.enabled:
            self._ok = self._init_mixer()
            if not self._ok:
                log.warning("audio device unavailable, sounds are disabled")

    @staticmethod
    def _init_mixer() -> bool:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.pre_init(frequency=44100, size=-16,
                                      channels=2, buffer=512)
                pygame.mixer.init()
            return True
        except pygame.error:
            return False

    def _get(self, path: str) -> pygame.mixer.Sound | None:
        sound = self._cache.get(path)
        if sound is None and path not in self._cache:
            try:
                sound = pygame.mixer.Sound(str(self._base / path))
            except (pygame.error, FileNotFoundError) as e:
                log.error("cannot load sound %s: %s", path, e)
            self._cache[path] = sound
        return sound

    def play(self, path: str | None, volume: float = 1.0) -> None:
        if not self._ok or path is None:
            return
        sound = self._get(path)
        if sound is not None:
            sound.set_volume(min(1.0, self._master * volume))
            sound.play()

    def play_loop(self, path: str | None, volume: float = 1.0) -> None:
        if not self._ok or path is None:
            return
        sound = self._get(path)
        if sound is None:
            return
        self.stop_loop()
        sound.set_volume(min(1.0, self._master * volume))
        self._loop_channel = sound.play(loops=-1)

    def stop_loop(self) -> None:
        if self._loop_channel is not None:
            self._loop_channel.stop()
            self._loop_channel = None
