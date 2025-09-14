"""Backward-compat wrapper for the Skeptic agent.

The Skeptic now lives under `judge.agents.moderator.debaters.skeptic` to
reflect that it operates under the Moderator orchestration.
"""

from judge.agents.moderator.debaters.skeptic import skeptic_agent  # re-export

__all__ = ["skeptic_agent"]
