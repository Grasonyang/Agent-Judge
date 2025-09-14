"""Backward-compat wrapper for debate layer debater."""

from judge.agents.debate.moderator.debaters.advocate import advocate_agent  # re-export

__all__ = ["advocate_agent"]
