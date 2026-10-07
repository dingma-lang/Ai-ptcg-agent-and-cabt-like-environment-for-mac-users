from adapters.cabt.submission_entry import agent as _cabt_agent


def agent(obs_dict: dict) -> list[int]:
    return _cabt_agent(obs_dict)


__all__ = ["agent"]
