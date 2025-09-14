"""Backward-compat wrapper for debate layer debater."""

from judge.agents.debate.moderator.debaters.devil import devil_agent  # re-export

__all__ = ["devil_agent"]
