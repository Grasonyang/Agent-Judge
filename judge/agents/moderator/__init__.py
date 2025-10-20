"""Moderator package

Exports the moderator orchestrator/loop and keeps debaters under this package,
following the architecture where the moderator controls Advocate/Skeptic/Devil.
"""

from .agent import orchestrator_agent, decision_agent, executor_agent, stop_checker, referee_loop

__all__ = [
    "orchestrator_agent",
    "decision_agent",
    "executor_agent",
    "stop_checker",
    "referee_loop",
]

