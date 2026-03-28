import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

try:
    from PyQt6.QtWidgets import QApplication
except ImportError as err:
    print("PyQt6 is not installed. Run: pip install -r game/requirements.txt")
    print(f"ImportError: {err}")
    raise SystemExit(1)

from game.ui.main_window import SnakeWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = SnakeWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
