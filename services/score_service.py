import json
from pathlib import Path


def load_high_score(file_path: Path) -> int:
    if not file_path.exists():
        return 0

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0

    score = data.get("high_score", 0)
    return score if isinstance(score, int) and score >= 0 else 0


def save_high_score(file_path: Path, score: int) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"high_score": max(0, int(score))}
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
