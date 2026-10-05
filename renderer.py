import random
from enum import Enum, auto
from pathlib import Path
import pygame
from config_schema import WindowConfig


class RenderState(Enum):
    IDLE = auto()
    SPINNING = auto()
    RESULT = auto()


class RenderEvent(Enum):
    SPIN_FINISHED = auto()
    RESULT_HIDDEN = auto()


class Renderer:
    FPS = 60

    def __init__(self, window_cfg: WindowConfig, card_paths: list[Path], overlay_path: Path | None = None):
        pygame.init()
        self.width = window_cfg.width
        self.height = window_cfg.height
        self.screen = pygame.display.set_mode((self.width, self.height), vsync=1)
        pygame.display.set_caption("Twitch Ban Roulette")

        self.key_color = tuple(window_cfg.chroma_key)
        self.card_w, self.card_h = window_cfg.card_size
        self.gap = window_cfg.gap

        self.clock = pygame.time.Clock()
        self.state = RenderState.IDLE

        self._load_assets(card_paths, overlay_path)

        self.strip: list[pygame.Surface] = []
        self.winner_index = 0
        self.spin_start_ms = 0
        self.spin_duration_ms = 0
        self.scroll_to = 0.0
        self.result_start_ms = 0
        self.result_hold_ms = 3000

        self._debug_spin = False

    def _load_assets(self, card_paths: list[Path], overlay_path: Path | None) -> None:
        self.cards = []
        for path in card_paths:
            img = pygame.image.load(str(path)).convert_alpha()
            img = pygame.transform.smoothscale(img, (self.card_w, self.card_h))
            self.cards.append(img)

        self.overlay = None
        if overlay_path is not None:
            img = pygame.image.load(str(overlay_path)).convert_alpha()
            self.overlay = pygame.transform.smoothscale(img, (self.width, self.height))

    def start_spin(self, sequence: list[int], winner_index: int, duration_s: float = 4.0) -> None:
        if self.state is not RenderState.IDLE:
            return
        self.strip = [self.cards[i] for i in sequence]
        self.winner_index = winner_index
        self.spin_start_ms = pygame.time.get_ticks()
        self.spin_duration_ms = int(duration_s * 1000)

        stride = self.card_w + self.gap
        jitter = random.uniform(-0.35, 0.35) * self.card_w
        self.scroll_to = (winner_index * stride
                          + self.card_w / 2
                          - self.width / 2
                          + jitter)
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
        self.screen.fill(self.key_color)
        frame_event = None

        if self.state is RenderState.SPINNING:
            self._draw_strip(self._current_scroll())
            self._draw_overlay()
            if self._spin_finished():
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
        self.clock.tick(self.FPS)
        return frame_event

    def _current_scroll(self) -> float:
        t = (pygame.time.get_ticks() - self.spin_start_ms) / self.spin_duration_ms
        t = min(t, 1.0)
        eased = 1 - (1 - t) ** 3
        return self.scroll_to * eased

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
        stride = self.card_w + self.gap
        x = int(self.winner_index * stride - self.scroll_to)
        y = (self.height - self.card_h) // 2
        rect = pygame.Rect(x - 3, y - 3, self.card_w + 6, self.card_h + 6)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 3)
