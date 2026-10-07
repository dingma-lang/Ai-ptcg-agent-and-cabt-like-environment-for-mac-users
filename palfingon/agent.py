try:
    from adapters.cabt.submission_entry import agent as _cabt_agent
except Exception:
    _cabt_agent = None


def agent(obs_dict: dict) -> list[int]:
    try:
        if _cabt_agent is not None:
            return _cabt_agent(obs_dict)
    except Exception:
        pass
    if not isinstance(obs_dict, dict):
        return []
    select = obs_dict.get("select")
    if not isinstance(select, dict):
        return []
    options = select.get("option")
    if not isinstance(options, list) or not options:
        return []
    try:
        minimum = min(len(options), max(0, int(select.get("minCount", 0) or 0)))
        maximum = min(len(options), max(minimum, int(select.get("maxCount", minimum) or minimum)))
    except (ValueError, TypeError):
        return []
    return list(range(min(minimum, maximum)))


__all__ = ["agent"]
