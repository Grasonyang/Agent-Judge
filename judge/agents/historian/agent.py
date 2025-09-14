"""Backward-compat wrapper for knowledge.historian agent."""

from judge.agents.knowledge.historian import historian_agent  # re-export

__all__ = ["historian_agent"]
