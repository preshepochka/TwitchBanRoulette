import random
from dataclasses import dataclass

from config_schema import Outcome, WindowConfig


@dataclass
class SpinPlan:
    sequence: list[int]
    winner_index: int
    winner_name: str


class Roulette:
    def __init__(self, outcomes: dict[str, Outcome], window_cfg: WindowConfig):
        self.names = list(outcomes.keys())
        self.weights = [outcomes[name].chance for name in self.names]
        self._index = {name: i for i, name in enumerate(self.names)}

        stride = window_cfg.card_size[0] + window_cfg.gap
        self._tail = window_cfg.width // stride + 2

    def pick_winner(self) -> str:
        return random.choices(self.names, weights=self.weights, k=1)[0]

    def generate_spin(self) -> SpinPlan:
        winner_name = self.pick_winner()
        winner_index = random.randint(20, 30)
        length = winner_index + self._tail

        # лента — случайная масса карточек, победитель в нужной позиции
        sequence = [random.randrange(len(self.names)) for _ in range(length)]
        sequence[winner_index] = self._index[winner_name]

        return SpinPlan(sequence=sequence,
                        winner_index=winner_index,
                        winner_name=winner_name)
