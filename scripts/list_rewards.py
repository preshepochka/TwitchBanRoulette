import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modes import list_rewards

if __name__ == "__main__":
    list_rewards()
