from game.services.game_service import GameState


def build_status_lines(state: GameState) -> tuple[str, str]:
    controls = "[Ben] Move: WASD / Arrows | Pause: P | Restart: R | Quit: Q or Esc"
    if state.game_over:
        summary = (
            f"Score: {state.score} | High Score: {state.high_score} | "
            f"Level: {state.level} | Game Over: {state.fail_reason}"
        )
    elif state.paused:
        summary = (
            f"Score: {state.score} | High Score: {state.high_score} | "
            f"Level: {state.level} | Paused"
        )
    else:
        bonus_text = "None" if state.bonus_food is None else f"{state.bonus_timer} ticks"
        summary = (
            f"Score: {state.score} | High Score: {state.high_score} | "
            f"Level: {state.level} | Speed: {state.tick_ms} ms | Bonus: {bonus_text}"
        )
    return summary, controls
