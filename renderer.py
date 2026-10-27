import random
from enum import Enum, auto
from pathlib import Path
import pygame
from audio import Audio
from config_schema import (ColorBackground, HighlightStyle, ImageBackground,
                           WindowConfig)


class RenderState(Enum):
    IDLE = auto()
    SPINNING = auto()
    RESULT = auto()


class RenderEvent(Enum):
    SPIN_FINISHED = auto()
    RESULT_HIDDEN = auto()


class Renderer:
    def __init__(self, window_cfg: WindowConfig, card_paths: list[Path],
                 overlay_path: Path | None = None,
                 background_path: Path | None = None,
                 audio: Audio | None = None):
        pygame.init()
        self.width = window_cfg.width
        self.height = window_cfg.height
        self.screen = pygame.display.set_mode((self.width, self.height), vsync=1)
        pygame.display.set_caption(window_cfg.title)

        self.key_color = tuple(window_cfg.chroma_key)
        self.card_w, self.card_h = window_cfg.card_size
        self.gap = window_cfg.gap
        self.highlight: HighlightStyle = window_cfg.highlight
        self.fps = window_cfg.fps
        self.spin_duration_ms = int(window_cfg.spin_duration * 1000)
        self.result_hold_ms = int(window_cfg.result_hold * 1000)
        self.audio = audio

        self.clock = pygame.time.Clock()
        self.state = RenderState.IDLE

        self._load_assets(window_cfg, card_paths, overlay_path, background_path)

        self.strip: list[pygame.Surface] = []
        self.winner_index = 0
        self.spin_start_ms = 0
        self.scroll_to = 0.0
        self.result_start_ms = 0
        self._last_card_under = 0

        self._debug_spin = False

    def _load_assets(self, window_cfg: WindowConfig, card_paths: list[Path],
                     overlay_path: Path | None,
                     background_path: Path | None) -> None:
        self.cards = [self._load_image(p, (self.card_w, self.card_h))
                      for p in card_paths]

        self.overlay = None
        if overlay_path is not None:
            self.overlay = self._load_image(overlay_path, (self.width, self.height))

        self.background_spec = window_cfg.background
        self.bg_surface = None
        if isinstance(self.background_spec, ImageBackground):
            if background_path is None:
                raise ValueError("background type is 'image' "
                                 "but no background path was provided")
            self.bg_surface = self._load_image(background_path,
                                               (self.width, self.height))

    @staticmethod
    def _load_image(path: Path, size: tuple[int, int]) -> pygame.Surface:
        try:
            img = pygame.image.load(str(path)).convert_alpha()
        except pygame.error as e:
            raise RuntimeError(
                f"cannot load image {path}: {e} "
                f"(file may be corrupted, or this pygame build has no PNG support; "
                f"try 'pip install pygame-ce' or Python 3.12/3.13)"
            ) from e
        return pygame.transform.smoothscale(img, size)

    def start_spin(self, sequence: list[int], winner_index: int) -> None:
        if self.state is RenderState.SPINNING:
            return
        self.strip = [self.cards[i] for i in sequence]
        self.winner_index = winner_index
        self.spin_start_ms = pygame.time.get_ticks()

        stride = self.card_w + self.gap
        jitter = random.uniform(-0.35, 0.35) * self.card_w
        self.scroll_to = (winner_index * stride
                          + self.card_w / 2
                          - self.width / 2
                          + jitter)
        self._last_card_under = int((self.width / 2) // stride)
        if self.audio is not None:
            self.audio.play_loop(self.audio.sounds.spin)
        self.state = RenderState.SPINNING

    def poll_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self._debug_spin = True
        return True

    def pop_debug_spin(self) -> bool:
        pressed, self._debug_spin = self._debug_spin, False
        return pressed

    def draw(self) -> RenderEvent | None:
        self._draw_background()
        frame_event = None

        if self.state is RenderState.SPINNING:
            scroll = self._current_scroll()
            self._tick_check(scroll)
            self._draw_strip(scroll)
            self._draw_overlay()
            if self._spin_finished():
                if self.audio is not None:
                    self.audio.stop_loop()
                self.state = RenderState.RESULT
                self.result_start_ms = pygame.time.get_ticks()
                frame_event = RenderEvent.SPIN_FINISHED

        elif self.state is RenderState.RESULT:
            self._draw_strip(self.scroll_to)
            self._highlight_winner()
            self._draw_overlay()
            if pygame.time.get_ticks() - self.result_start_ms >= self.result_hold_ms:
                self.state = RenderState.IDLE
                frame_event = RenderEvent.RESULT_HIDDEN

        pygame.display.flip()
        self.clock.tick(self.fps)
        return frame_event

    def _draw_background(self) -> None:
        if self.bg_surface is not None:
            self.screen.blit(self.bg_surface, (0, 0))
        elif isinstance(self.background_spec, ColorBackground):
            self.screen.fill(tuple(self.background_spec.color))
        else:
            self.screen.fill(self.key_color)

    def _current_scroll(self) -> float:
        t = (pygame.time.get_ticks() - self.spin_start_ms) / self.spin_duration_ms
        t = min(t, 1.0)
        eased = 1 - (1 - t) ** 3
        return self.scroll_to * eased

    def _tick_check(self, scroll: float) -> None:
        if self.audio is None or self.audio.sounds.tick is None:
            return
        stride = self.card_w + self.gap
        card_under = int((scroll + self.width / 2) // stride)
        if card_under != self._last_card_under:
            self._last_card_under = card_under
            self.audio.play(self.audio.sounds.tick)

    def _spin_finished(self) -> bool:
        return (pygame.time.get_ticks() - self.spin_start_ms) >= self.spin_duration_ms

    def _draw_strip(self, scroll: float) -> None:
        stride = self.card_w + self.gap
        y = (self.height - self.card_h) // 2
        for i, card in enumerate(self.strip):
            x = int(i * stride - scroll)
            if -stride < x < self.width + stride:
                self.screen.blit(card, (x, y))

    def _draw_overlay(self) -> None:
        if self.overlay is not None:
            self.screen.blit(self.overlay, (0, 0))
        else:
            cx = self.width // 2
            pygame.draw.line(self.screen, (255, 255, 255), (cx, 0), (cx, self.height), 3)

    def _highlight_winner(self) -> None:
        if not self.highlight.enabled:
            return
        stride = self.card_w + self.gap
        x = int(self.winner_index * stride - self.scroll_to)
        y = (self.height - self.card_h) // 2
        rect = pygame.Rect(x - 3, y - 3, self.card_w + 6, self.card_h + 6)
        pygame.draw.rect(self.screen, tuple(self.highlight.color), rect,
                         self.highlight.thickness,
                         border_radius=self.highlight.radius)
