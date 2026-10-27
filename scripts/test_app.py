import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modes import run_app_test

if __name__ == "__main__":
    run_app_test()
