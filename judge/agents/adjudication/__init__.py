"""Adjudication layer: Evidence, Jury, Synthesizer.

This package groups the agents that verify, judge, and synthesize
outputs from the debate and social simulation.
"""

from .evidence.agent import evidence_agent
from .jury.agent import jury_agent
from .synthesizer.agent import synthesizer_agent
from .agent import adjudication_agent

__all__ = [
    "evidence_agent",
    "jury_agent",
    "synthesizer_agent",
    "adjudication_agent",
]
