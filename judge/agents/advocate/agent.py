"""Backward-compat wrapper for the Advocate agent.

The Advocate now lives under `judge.agents.moderator.debaters.advocate` to
better reflect the architecture (debater agents under Moderator).
Importing here preserves older import paths.
"""

from judge.agents.moderator.debaters.advocate import advocate_agent  # re-export

__all__ = ["advocate_agent"]
