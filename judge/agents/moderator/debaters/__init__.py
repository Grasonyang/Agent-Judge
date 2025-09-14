"""Debaters under Moderator namespace.

This package groups the core debate agents that operate under the
Moderator's orchestration: Advocate, Skeptic, and Devil's Advocate.

Keeping them colocated clarifies ownership and simplifies imports
from moderator tooling (AgentTool wrappers, loop orchestration, etc.).
"""

from .advocate import advocate_agent
from .skeptic import skeptic_agent
from .devil import devil_agent

__all__ = [
    "advocate_agent",
    "skeptic_agent",
    "devil_agent",
]

