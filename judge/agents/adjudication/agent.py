"""Adjudication workflow agent

Composes the Evidence -> Jury -> Synthesizer flow into a single
SequentialAgent, matching the architecture's Judgment layer design.
"""

from google.adk.agents import SequentialAgent

from .evidence.agent import evidence_agent
from .jury.agent import jury_agent
from .synthesizer.agent import synthesizer_agent


adjudication_agent = SequentialAgent(
    name="adjudication",
    sub_agents=[evidence_agent, jury_agent, synthesizer_agent],
)

__all__ = ["adjudication_agent"]

