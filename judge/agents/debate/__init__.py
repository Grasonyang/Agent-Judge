"""Core Debate Arena.

Holds the moderator orchestration and its debaters under a single
namespace for clarity and easier maintenance.
"""

from .moderator.agent import orchestrator_agent, referee_loop

__all__ = ["orchestrator_agent", "referee_loop"]

