from __future__ import annotations

from dataclasses import dataclass
from random import choice
from typing import Optional

from game.config.app_config import (
    BONUS_FOOD_FREQUENCY,
    BONUS_FOOD_SCORE,
    BONUS_LIFETIME_TICKS,
    GRID_HEIGHT,
    GRID_WIDTH,
    INIT_LENGTH,
    INITIAL_TICK_MS,
    LEVEL_UP_EVERY,
    MIN_TICK_MS,
    NORMAL_FOOD_SCORE,
    SPEED_STEP_MS,
    START_DIRECTION,
    START_X,
    START_Y,
)

Cell = tuple[int, int]
Vector = tuple[int, int]

DIRECTIONS: dict[str, Vector] = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


@dataclass
class TickResult:
    ate_food: bool = False
    ate_bonus: bool = False
    level_up: bool = False
    new_high_score: bool = False


@dataclass
class GameState:
    snake: list[Cell]
    direction: Vector
    pending_direction: Vector
    food: Cell
    bonus_food: Optional[Cell]
    hazard: Cell
    bonus_timer: int
    score: int
    high_score: int
    foods_eaten: int
    level: int
    tick_ms: int
    game_over: bool
    paused: bool
    fail_reason: Optional[str]
    obstacles: set[Cell]


def create_initial_snake(length: int, start_x: int, start_y: int, direction_name: str) -> list[Cell]:
    dx, dy = DIRECTIONS[direction_name]
    snake: list[Cell] = []
    for i in range(length):
        snake.append((start_x - dx * i, start_y - dy * i))
    return snake


def is_opposite(d1: Vector, d2: Vector) -> bool:
    return d1[0] + d2[0] == 0 and d1[1] + d2[1] == 0


def create_new_game(high_score: int) -> GameState:
    snake = create_initial_snake(INIT_LENGTH, START_X, START_Y, START_DIRECTION)
    obstacles = generate_obstacles(1, snake)
    food = spawn_food(snake, obstacles)
    hazard = spawn_food(snake, obstacles, extra_blocked={food})
    return GameState(
        snake=snake,
        direction=DIRECTIONS[START_DIRECTION],
        pending_direction=DIRECTIONS[START_DIRECTION],
        food=food,
        bonus_food=None,
        hazard=hazard,
        bonus_timer=0,
        score=0,
        high_score=high_score,
        foods_eaten=0,
        level=1,
        tick_ms=INITIAL_TICK_MS,
        game_over=False,
        paused=False,
        fail_reason=None,
        obstacles=obstacles,
    )


def spawn_food(snake: list[Cell], obstacles: set[Cell], extra_blocked: Optional[set[Cell]] = None) -> Cell:
    blocked = set(snake) | set(obstacles)
    if extra_blocked:
        blocked |= extra_blocked

    candidates = [
        (x, y)
        for y in range(GRID_HEIGHT)
        for x in range(GRID_WIDTH)
        if (x, y) not in blocked
    ]
    if not candidates:
        raise RuntimeError("No empty cell left on the board.")
    return choice(candidates)


def generate_obstacles(level: int, snake: list[Cell]) -> set[Cell]:
    patterns: dict[int, set[Cell]] = {
        1: set(),
        2: {(12, 4), (12, 5), (12, 6), (12, 9), (12, 10), (12, 11)},
        3: {
            (8, 4), (8, 5), (8, 6),
            (15, 9), (15, 10), (15, 11),
            (11, 7), (12, 7), (13, 7),
        },
        4: {
            (5, 5), (6, 5), (7, 5),
            (16, 10), (17, 10), (18, 10),
            (11, 3), (11, 4), (11, 5),
            (13, 10), (13, 11), (13, 12),
        },
    }
    pattern = patterns.get(min(level, 4), patterns[4])
    snake_cells = set(snake)
    return {cell for cell in pattern if cell not in snake_cells}


def queue_direction(state: GameState, candidate: Vector) -> None:
    if not is_opposite(state.direction, candidate):
        state.pending_direction = candidate


def toggle_pause(state: GameState) -> None:
    if not state.game_over:
        state.paused = not state.paused


def advance_game(state: GameState) -> TickResult:
    result = TickResult()
    if state.game_over or state.paused:
        return result

    state.direction = state.pending_direction
    head_x, head_y = state.snake[0]
    dx, dy = state.direction
    new_head = (head_x + dx, head_y + dy)

    if not (0 <= new_head[0] < GRID_WIDTH and 0 <= new_head[1] < GRID_HEIGHT):
        state.game_over = True
        state.fail_reason = "Hit the wall"
        return result

    if new_head in state.obstacles:
        state.game_over = True
        state.fail_reason = "Crashed into obstacle"
        return result

    if new_head == state.hazard:
        state.game_over = True
        state.fail_reason = "Hit the red hazard"
        return result

    ate_food = new_head == state.food
    ate_bonus = state.bonus_food is not None and new_head == state.bonus_food
    body_to_check = state.snake if ate_food or ate_bonus else state.snake[:-1]
    if new_head in body_to_check:
        state.game_over = True
        state.fail_reason = "Bit itself"
        return result

    state.snake.insert(0, new_head)
    if ate_food:
        result.ate_food = True
        state.score += NORMAL_FOOD_SCORE
        state.foods_eaten += 1
        _handle_food_progress(state, result)
    elif ate_bonus:
        result.ate_bonus = True
        state.score += BONUS_FOOD_SCORE
        state.bonus_food = None
        state.bonus_timer = 0
    else:
        state.snake.pop()

    if not ate_food and not ate_bonus:
        _update_bonus_timer(state)

    if state.score > state.high_score:
        state.high_score = state.score
        result.new_high_score = True

    return result


def _handle_food_progress(state: GameState, result: TickResult) -> None:
    next_level = state.foods_eaten // LEVEL_UP_EVERY + 1
    if next_level > state.level:
        state.level = next_level
        state.tick_ms = max(MIN_TICK_MS, state.tick_ms - SPEED_STEP_MS)
        state.obstacles = generate_obstacles(state.level, state.snake)
        result.level_up = True

    extra_blocked = {state.hazard}
    if state.bonus_food is not None:
        extra_blocked.add(state.bonus_food)
    state.food = spawn_food(state.snake, state.obstacles, extra_blocked=extra_blocked)

    if state.foods_eaten % BONUS_FOOD_FREQUENCY == 0:
        state.bonus_food = spawn_food(
            state.snake,
            state.obstacles,
            extra_blocked={state.food, state.hazard},
        )
        state.bonus_timer = BONUS_LIFETIME_TICKS
    else:
        _update_bonus_timer(state)

    blocked_for_hazard = {state.food}
    if state.bonus_food is not None:
        blocked_for_hazard.add(state.bonus_food)
    state.hazard = spawn_food(state.snake, state.obstacles, extra_blocked=blocked_for_hazard)


def _update_bonus_timer(state: GameState) -> None:
    if state.bonus_food is None:
        return

    state.bonus_timer -= 1
    if state.bonus_timer <= 0:
        state.bonus_food = None
        state.bonus_timer = 0
