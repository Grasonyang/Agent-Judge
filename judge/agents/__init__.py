"""
Agents package: 聚合所有子代理
"""

from .moderator.advocate.agent import advocate_agent
from .knowledge.curator import curator_agent
from .knowledge.historian import historian_agent
from .moderator.devil.agent import devil_agent
from .adjudication.jury import jury_agent
from .moderator.agent import orchestrator_agent, referee_loop
from .moderator.skeptic.agent import skeptic_agent
from .adjudication.synthesizer.agent import synthesizer_agent
from .social.agent import social_summary_agent
from .social.noise.agent import social_noise_agent
from .adjudication.evidence import evidence_agent

__all__ = [
    "advocate_agent",
    "curator_agent",
    "historian_agent",
    "devil_agent",
    "jury_agent",
    "orchestrator_agent",
    "referee_loop",
    "skeptic_agent",
    "synthesizer_agent",
    "social_summary_agent",
    "social_noise_agent",
    "evidence_agent",
]
