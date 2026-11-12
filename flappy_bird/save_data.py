import json
from pathlib import Path

SAVE_PATH = Path(__file__).resolve().parent.parent / "save_data.json"


def default_state():
    return {
        "coins": 0,
        "high_score": 0,
        "selected_bird": "classic",
        "selected_scene": "classic",
        "unlocked_birds": ["classic"],
        "unlocked_scenes": ["classic"],
        "achievements": {},
        "settings": {
            "master_volume": 0.8,
            "music_volume": 0.7,
            "sfx_volume": 0.8,
            "fullscreen": False,
            "window_width": 1280,
            "window_height": 720,
            "fps_limit": 60,
            "particles_enabled": True,
            "difficulty": "normal",
        },
        "stats": {
            "games_played": 0,
            "total_obstacles_passed": 0,
            "total_coins_collected": 0,
            "total_coins_earned": 0,
            "scenes_played": {},
        },
    }


def load_state():
    if not SAVE_PATH.exists():
        data = default_state()
        save_state(data)
        return data

    try:
        with SAVE_PATH.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (json.JSONDecodeError, OSError):
        data = default_state()
        save_state(data)
        return data

    state = default_state()
    for key, value in loaded.items():
        if key in state:
            if isinstance(state[key], dict) and isinstance(value, dict):
                state[key].update(value)
            else:
                state[key] = value

    if "unlocked_birds" not in loaded or not loaded.get("unlocked_birds"):
        state["unlocked_birds"] = ["classic"]
    if "unlocked_scenes" not in loaded or not loaded.get("unlocked_scenes"):
        state["unlocked_scenes"] = ["classic"]

    return state


def save_state(state):
    try:
        with SAVE_PATH.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
    except OSError:
        return False
    return True
