"""Backward-compat wrapper for the Devil's Advocate agent.

The Devil agent now lives under `judge.agents.moderator.debaters.devil` to
live alongside the other debaters.
"""

from judge.agents.moderator.debaters.devil import devil_agent  # re-export

__all__ = ["devil_agent"]
