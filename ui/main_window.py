import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

from game.config.app_config import (
    APP_TITLE,
    BOARD_COLOR,
    BONUS_FOOD_COLOR,
    CELL_SIZE,
    FOOD_COLOR,
    GRID_HEIGHT,
    GRID_LINE_COLOR,
    GRID_WIDTH,
    HAZARD_COLOR,
    HIGH_SCORE_FILE,
    OBSTACLE_COLOR,
    SNAKE_BODY_COLOR,
    SNAKE_HEAD_COLOR,
    STATUS_HEIGHT,
    TEXT_COLOR,
)
from game.services.game_service import DIRECTIONS, advance_game, create_new_game, queue_direction, toggle_pause
from game.services.score_service import load_high_score, save_high_score

try:
    from .helpers import build_status_lines
except ImportError:
    from game.ui.helpers import build_status_lines


class SnakeWindow(QWidget):
    KEY_TO_DIRECTION = {
        int(Qt.Key.Key_W): DIRECTIONS["up"],
        int(Qt.Key.Key_S): DIRECTIONS["down"],
        int(Qt.Key.Key_A): DIRECTIONS["left"],
        int(Qt.Key.Key_D): DIRECTIONS["right"],
        int(Qt.Key.Key_Up): DIRECTIONS["up"],
        int(Qt.Key.Key_Down): DIRECTIONS["down"],
        int(Qt.Key.Key_Left): DIRECTIONS["left"],
        int(Qt.Key.Key_Right): DIRECTIONS["right"],
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setFixedSize(GRID_WIDTH * CELL_SIZE, GRID_HEIGHT * CELL_SIZE + STATUS_HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)

        self.title_font = QFont("Consolas", 11)
        self.body_font = QFont("Consolas", 9)

        self.high_score = load_high_score(HIGH_SCORE_FILE)
        self.state = create_new_game(self.high_score)
        self.timer.start(self.state.tick_ms)

    def reset_game(self) -> None:
        self.state = create_new_game(self.high_score)
        self.timer.start(self.state.tick_ms)
        self.update()

    def keyPressEvent(self, event):  # type: ignore[override]
        key = int(event.key())

        if key in (int(Qt.Key.Key_Q), int(Qt.Key.Key_Escape)):
            self.close()
            return

        if key == int(Qt.Key.Key_R):
            self.reset_game()
            return

        if key == int(Qt.Key.Key_P):
            toggle_pause(self.state)
            self.update()
            return

        if key in self.KEY_TO_DIRECTION and not self.state.game_over:
            queue_direction(self.state, self.KEY_TO_DIRECTION[key])

    def on_tick(self) -> None:
        previous_tick_ms = self.state.tick_ms
        result = advance_game(self.state)

        if result.new_high_score:
            self.high_score = self.state.high_score
            save_high_score(HIGH_SCORE_FILE, self.high_score)

        if self.state.game_over:
            self.timer.stop()
            if self.state.high_score > self.high_score:
                self.high_score = self.state.high_score
                save_high_score(HIGH_SCORE_FILE, self.high_score)
        elif self.state.tick_ms != previous_tick_ms:
            self.timer.start(self.state.tick_ms)

        self.update()

    def paintEvent(self, _event):  # type: ignore[override]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(*BOARD_COLOR))
        self.draw_status(painter)
        self.draw_board(painter)

    def draw_status(self, painter: QPainter) -> None:
        summary, controls = build_status_lines(self.state)
        painter.setPen(QColor(*TEXT_COLOR))
        painter.setFont(self.title_font)
        painter.drawText(12, 28, summary)
        painter.setFont(self.body_font)
        painter.drawText(12, 56, controls)

    def draw_board(self, painter: QPainter) -> None:
        top = STATUS_HEIGHT
        board_width = GRID_WIDTH * CELL_SIZE
        board_height = GRID_HEIGHT * CELL_SIZE

        painter.setPen(QPen(QColor(*GRID_LINE_COLOR), 1))
        for x in range(GRID_WIDTH + 1):
            px = x * CELL_SIZE
            painter.drawLine(px, top, px, top + board_height)
        for y in range(GRID_HEIGHT + 1):
            py = top + y * CELL_SIZE
            painter.drawLine(0, py, board_width, py)

        for ox, oy in self.state.obstacles:
            self.draw_cell(painter, ox, oy, QColor(*OBSTACLE_COLOR), top, padding=4)

        fx, fy = self.state.food
        self.draw_cell(painter, fx, fy, QColor(*FOOD_COLOR), top, padding=4)

        if self.state.bonus_food is not None:
            bx, by = self.state.bonus_food
            self.draw_cell(painter, bx, by, QColor(*BONUS_FOOD_COLOR), top, padding=2)

        rx, ry = self.state.hazard
        self.draw_hazard(painter, rx, ry, top)

        hx, hy = self.state.snake[0]
        self.draw_cell(painter, hx, hy, QColor(*SNAKE_HEAD_COLOR), top, padding=3)
        for sx, sy in self.state.snake[1:]:
            self.draw_cell(painter, sx, sy, QColor(*SNAKE_BODY_COLOR), top, padding=4)

    def draw_cell(self, painter: QPainter, x: int, y: int, color: QColor, top: int, padding: int) -> None:
        px = x * CELL_SIZE + padding
        py = top + y * CELL_SIZE + padding
        size = CELL_SIZE - padding * 2
        painter.fillRect(px, py, size, size, color)

    def draw_hazard(self, painter: QPainter, x: int, y: int, top: int) -> None:
        px = x * CELL_SIZE
        py = top + y * CELL_SIZE

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        skull_color = QColor(244, 240, 232)
        outline_color = QColor(*HAZARD_COLOR)
        feature_color = QColor(45, 18, 18)

        painter.setPen(QPen(outline_color, 2))
        painter.setBrush(skull_color)
        painter.drawEllipse(px + 4, py + 2, CELL_SIZE - 8, CELL_SIZE - 10)
        painter.drawRoundedRect(px + 7, py + 15, CELL_SIZE - 14, 9, 2, 2)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(feature_color)
        painter.drawEllipse(px + 8, py + 9, 5, 6)
        painter.drawEllipse(px + 15, py + 9, 5, 6)
        painter.drawConvexPolygon(
            QPoint(px + 14, py + 14),
            QPoint(px + 11, py + 18),
            QPoint(px + 17, py + 18),
        )

        painter.setBrush(outline_color)
        painter.fillRect(px + 10, py + 18, 1, 5, outline_color)
        painter.fillRect(px + 13, py + 18, 1, 5, outline_color)
        painter.fillRect(px + 16, py + 18, 1, 5, outline_color)

        painter.restore()


def main() -> None:
    app = QApplication(sys.argv)
    window = SnakeWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
