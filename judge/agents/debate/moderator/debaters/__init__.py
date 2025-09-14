"""Debaters under Moderator namespace (in Debate layer)."""

from .advocate import advocate_agent
from .skeptic import skeptic_agent
from .devil import devil_agent

__all__ = [
    "advocate_agent",
    "skeptic_agent",
    "devil_agent",
]

