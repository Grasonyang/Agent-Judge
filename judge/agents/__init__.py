"""
Agents package: 聚合所有子代理
"""

#from .moderator.advocate.agent import advocate_agent
from .knowledge.curator import curator_agent
from .knowledge.historian import historian_agent
from .moderator.devil.agent import devil_agent
from .adjudication.jury import jury_agent
from .moderator.agent import orchestrator_agent
#from .moderator.skeptic.agent import skeptic_agent
from .adjudication.synthesizer.agent import synthesizer_agent
from .social.agent import social_summary_agent
from .social.noise.agent import social_noise_agent
from .adjudication.evidence import evidence_agent
from .moderator.skeptic.agent import skeptic_agent1
from .moderator.skeptic2.agent import skeptic_agent2
from .moderator.skeptic3.agent import skeptic_agent3
from .moderator.skeptic4.agent import skeptic_agent4
from .moderator.advocate.agent import advocate_agent1
from .moderator.advocate2.agent import advocate_agent2    
from .moderator.advocate3.agent import advocate_agent3
from .moderator.advocate4.agent import advocate_agent4


__all__ = [
    "advocate_agent1",
    "advocate_agent2",
    "advocate_agent3",
    "advocate_agent4",
    "curator_agent",
    "historian_agent",
    "devil_agent",
    "jury_agent",
    "orchestrator_agent",
    "referee_loop",
    "skeptic_agent1",
    "skeptic_agent2",
    "skeptic_agent3",
    "skeptic_agent4",
    "synthesizer_agent",
    "social_summary_agent",
    "social_noise_agent",
    "evidence_agent",
]
