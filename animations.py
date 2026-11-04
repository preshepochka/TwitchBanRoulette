import logging
from pathlib import Path

import pygame

log = logging.getLogger(__name__)

try:
    from PIL import Image
except ImportError:  # pillow is optional at runtime
    Image = None


class Animation:
    """A loopable frame animation loaded from a gif/webp/apng file."""

    def __init__(self, frames: list[pygame.Surface], durations_ms: list[int]):
        self.frames = frames
        self.durations_ms = durations_ms
        self.total_ms = sum(durations_ms)

    def frame_at(self, ms: int) -> pygame.Surface | None:
        """Frame shown at time ms (loops forever)."""
        if not self.frames:
            return None
        t = ms % self.total_ms
        for frame, dur in zip(self.frames, self.durations_ms):
            if t < dur:
                return frame
            t -= dur
        return self.frames[-1]


def load_animation(path: Path, size: tuple[int, int]) -> Animation | None:
    """Load an animated image, scaled to size. None if Pillow is missing.

    Transparency is preserved: pixel alpha works in gif/webp/apng. GIF
    cannot store semi-transparent pixels (palette format) — use webp/apng
    for smooth edges. Frame durations come from the file itself.
    """
    if Image is None:
        log.warning("animation %s skipped: pillow is not installed "
                    "(pip install pillow)", path)
        return None
    try:
        img = Image.open(str(path))
    except Exception as e:
        raise RuntimeError(f"cannot open animation {path}: {e}") from e

    frames: list[pygame.Surface] = []
    durations: list[int] = []
    frame_count = getattr(img, "n_frames", 1)
    for i in range(frame_count):
        img.seek(i)
        rgba = img.convert("RGBA")
        frame = pygame.image.frombytes(
            rgba.tobytes(), rgba.size, "RGBA")
        frames.append(pygame.transform.smoothscale(frame, size))
        durations.append(max(20, int(img.info.get("duration", 100))))
    log.info("animation loaded: %s (%d frames)", path.name, len(frames))
    return Animation(frames, durations)
