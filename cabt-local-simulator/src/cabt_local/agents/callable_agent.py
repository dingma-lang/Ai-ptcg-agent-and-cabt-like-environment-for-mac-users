from __future__ import annotations

import importlib
from typing import Callable

from .base import AgentWrapper
from .random_agent import RandomAgent


def load_module_function(spec: str) -> Callable[[dict], list[int]]:
    if spec.startswith("module:"):
        spec = spec[len("module:") :]
    module_name, sep, func_name = spec.partition(":")
    if not sep:
        raise ValueError("Module agent spec must look like module:package.module:function")
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)
    if not callable(func):
        raise TypeError(f"{spec} is not callable")
    return func


def make_callable_agent(spec: str, timeout_s: float = 5.0) -> AgentWrapper:
    fallback = RandomAgent(seed=0)
    return AgentWrapper(load_module_function(spec), fallback, agent_id=spec, timeout_s=timeout_s)

