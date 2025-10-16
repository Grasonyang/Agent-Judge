"""
Moderator orchestrator: 三輪辯論流程
第一輪：Advocate 論述 -> Skeptic 論述
第二輪：Advocate 質疑 -> Skeptic 回應 -> Skeptic 質疑 -> Advocate 回應
第三輪：Advocate 總結 -> Skeptic 總結
"""
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent
from google.genai import types
from .skeptic.agent import skeptic_agent1
from .skeptic2.agent import skeptic_agent2
from .skeptic3.agent import skeptic_agent3
from .skeptic4.agent import skeptic_agent4
from .advocate.agent import advocate_agent1
from .advocate2.agent import advocate_agent2    
from .advocate3.agent import advocate_agent3
from .advocate4.agent import advocate_agent4

from .tools import (
    exit_loop,
    ensure_debate_messages,
)
from judge.agents.social.noise.agent import social_noise_agent




orchestrator_agent = SequentialAgent(
    name="moderator_orchestrator",
    sub_agents=[advocate_agent1, skeptic_agent1, advocate_agent2, skeptic_agent2, skeptic_agent3, advocate_agent3, advocate_agent4, skeptic_agent4],
)


