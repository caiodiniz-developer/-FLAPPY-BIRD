from flappy_bird.config import ACHIEVEMENTS


def _current_value(state, kind):
    if kind == "games_played":
        return state["stats"]["games_played"]
    if kind == "best_score":
        return state["high_score"]
    if kind == "coins_total":
        return state["stats"]["total_coins_collected"]
    if kind == "wallet":
        return state["coins"]
    if kind == "pipes_passed":
        return state["stats"]["total_obstacles_passed"]
    if kind == "scenarios_played":
        return len(state["stats"].get("scenes_played", {}))
    return 0


def evaluate_achievements(state):
    unlocked = state.get("achievements", {})
    notifications = []

    for item in ACHIEVEMENTS:
        aid = item["id"]
        if aid in unlocked and unlocked[aid].get("unlocked"):
            continue

        progress = _current_value(state, item["kind"])
        if progress >= item["requirement"]:
            unlocked[aid] = {"unlocked": True, "progress": progress}
            state["coins"] += item["reward"]
            notifications.append(item["name"])
        else:
            unlocked[aid] = {"unlocked": False, "progress": progress}

    state["achievements"] = unlocked
    return notifications
