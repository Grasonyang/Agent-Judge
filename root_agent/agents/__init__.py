"""
Agents package: 聚合所有子代理
"""

from .advocate.agent import advocate_agent
from .curator.agent import curator_agent
from .historian.agent import historian_agent
from .devil.agent import devil_agent
from .jury.agent import jury_agent
from .moderator.agent import orchestrator_agent, referee_loop
from .skeptic.agent import skeptic_agent
from .synthesizer.agent import synthesizer_agent
from .social.agent import social_summary_agent
from .social_noise.agent import social_noise_agent

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
]
