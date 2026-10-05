import pygame
from pathlib import Path
from config_manager import ConfigManager
CARDS = {
    "timeout": (255, 140, 0),
    "ban":     (220, 0, 60),
    "message": (0, 140, 255),
}


def make_card(path: Path, color: tuple) -> None:
    surf = pygame.Surface((150, 150), pygame.SRCALPHA)
    surf.fill((*color, 255))
    pygame.draw.rect(surf, (255, 255, 255), surf.get_rect(), 4)
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(path))


def make_overlay(path: Path, w: int, h: int) -> None:
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = w // 2
    pygame.draw.polygon(surf, (255, 255, 255, 255), [(cx - 20, 0), (cx + 20, 0), (cx, 38)])
    pygame.draw.rect(surf, (255, 255, 255, 200), surf.get_rect(), 4)
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(path))

if __name__ == "__main__":
    pygame.init()
    for name, color in CARDS.items():
        make_card(Path(f"assets/cards/{name}.png"), color)
    cfg = ConfigManager("config.json").load()
    make_overlay(Path("assets/overlay.png"), cfg.window.width, cfg.window.height)
    print("Placeholders created")
