"""Backward-compat wrapper module for moderator tools now under debate layer."""

from judge.agents.debate.moderator.tools import (
    exit_loop,
    ensure_debate_messages,
    advocate_tool,
    skeptic_tool,
    devil_tool,
    NextTurnDecision,
    log_tool_output,
)

__all__ = [
    "exit_loop",
    "ensure_debate_messages",
    "advocate_tool",
    "skeptic_tool",
    "devil_tool",
    "NextTurnDecision",
    "log_tool_output",
]

