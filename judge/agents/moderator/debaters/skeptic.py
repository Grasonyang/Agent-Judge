"""Backward-compat wrapper for debate layer debater."""

from judge.agents.debate.moderator.debaters.skeptic import skeptic_agent  # re-export

__all__ = ["skeptic_agent"]
