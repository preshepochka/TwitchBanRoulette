import math
import random
from enum import Enum, auto
from pathlib import Path
import pygame
from animations import Animation, load_animation
from audio import Audio
from config_schema import (ColorBackground, ConfettiStyle, HighlightStyle,
                           ImageBackground, WindowConfig)


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
                 audio: Audio | None = None,
                 outcome_animations: dict[int, Animation] | None = None):
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

        self._load_assets(window_cfg, card_paths, overlay_path, background_path,
                          outcome_animations)

        self.strip: list[pygame.Surface] = []
        self.winner_index = 0
        self.spin_start_ms = 0
        self.scroll_to = 0.0
        self.result_start_ms = 0
        self._last_card_under = 0

        # winner effects
        self.winner_effect = window_cfg.winner_effect
        self.confetti_cfg: ConfettiStyle = window_cfg.confetti
        self._effect: str = "none"          # active effect for this result
        self._confetti: list[list[float]] = []  # [x, y, vx, vy, color_idx]
        self._animations: dict[int, Animation] = outcome_animations or {}

        self._debug_spin = False

    def _load_assets(self, window_cfg: WindowConfig, card_paths: list[Path],
                     overlay_path: Path | None,
                     background_path: Path | None,
                     outcome_animations: dict[int, Animation] | None = None) -> None:
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

    def start_spin(self, sequence: list[int], winner_index: int,
                   animation: Animation | None = None,
                   effect: str | None = None) -> None:
        if self.state is RenderState.SPINNING:
            return
        self.strip = [self.cards[i] for i in sequence]
        self.winner_index = winner_index
        self.spin_start_ms = pygame.time.get_ticks()
        self._winner_animation = animation
        self._effect = effect if effect is not None else self.winner_effect

        stride = self.card_w + self.gap
        jitter = random.uniform(-0.35, 0.35) * self.card_w
        self.scroll_to = (winner_index * stride
                          + self.card_w / 2
                          - self.width / 2
                          + jitter)
        self._last_card_under = int((self.width / 2) // stride)
        self._confetti = []
        if self.audio is not None:
            self.audio.play_loop(self.audio.sounds.spin)
        self.state = RenderState.SPINNING
        return

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
            scroll = self._result_scroll()
            self._draw_strip(scroll)
            self._highlight_winner(scroll)
            self._draw_effect()
            self._draw_winner_animation()
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

    def _result_scroll(self) -> float:
        """Scroll offset during RESULT: shake effect offsets the strip."""
        if self._effect != "shake":
            return self.scroll_to
        t = (pygame.time.get_ticks() - self.result_start_ms) / 1000
        if t >= 0.6:
            return self.scroll_to
        decay = 1.0 - t / 0.6
        amp = 14 * decay * decay
        return self.scroll_to + random.uniform(-amp, amp)

    def _winner_rect(self, scroll: float) -> pygame.Rect:
        stride = self.card_w + self.gap
        x = int(self.winner_index * stride - scroll)
        y = (self.height - self.card_h) // 2
        return pygame.Rect(x, y, self.card_w, self.card_h)

    def _draw_effect(self) -> None:
        """Built-in winner effects, drawn over the strip."""
        if self._effect == "confetti" and self.confetti_cfg.count > 0:
            self._draw_confetti()
        elif self._effect == "pulse":
            self._draw_pulse()

    def _draw_pulse(self) -> None:
        t = (pygame.time.get_ticks() - self.result_start_ms) / 1000
        scale = 1.0 + 0.08 * abs(math.sin(t * 4))
        rect = self._winner_rect(self.scroll_to)
        card = self.strip[self.winner_index]
        grown = pygame.transform.smoothscale(
            card, (int(rect.w * scale), int(rect.h * scale)))
        self.screen.blit(grown, grown.get_rect(center=rect.center))

    def _draw_confetti(self) -> None:
        now = pygame.time.get_ticks()
        if not self._confetti:
            for _ in range(self.confetti_cfg.count):
                self._confetti.append([
                    random.uniform(0, self.width),   # x
                    random.uniform(-self.height, 0), # y
                    random.uniform(-40, 40),         # vx px/s
                    random.uniform(120, 320),        # vy px/s
                    random.randrange(len(self.confetti_cfg.colors)),
                ])
            self._confetti_t = now
        dt = (now - self._confetti_t) / 1000
        self._confetti_t = now
        size = max(3, self.height // 60)
        for p in self._confetti:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            if p[1] > self.height:
                p[1] = -size
                p[0] = random.uniform(0, self.width)
            color = self.confetti_cfg.colors[int(p[4])]
            pygame.draw.rect(self.screen, color,
                             (p[0], p[1], size, size * 2 // 3))

    def _draw_winner_animation(self) -> None:
        anim = getattr(self, "_winner_animation", None)
        if anim is None:
            return
        ms = pygame.time.get_ticks() - self.result_start_ms
        frame = anim.frame_at(ms)
        if frame is not None:
            self.screen.blit(frame, (0, 0))

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

    def _highlight_winner(self, scroll: float) -> None:
        if not self.highlight.enabled:
            return
        rect = self._winner_rect(scroll).inflate(6, 6)
        pygame.draw.rect(self.screen, tuple(self.highlight.color), rect,
                         self.highlight.thickness,
                         border_radius=self.highlight.radius)
