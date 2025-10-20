from google.adk.agents import ParallelAgent
from .echo.agent import echo_agent
from .influencer.agent import create_influencer_agent
from .disrupter.agent import create_disrupter_agent


def create_social_agent(influencer_count: int, include_noise: bool) -> ParallelAgent:
    """建立社群擴散的基礎流程

    Args:
        influencer_count: 意見領袖的數量
        include_noise: 是否紀錄噪音輸出
    """
    # Echo Chamber：模擬不同社群群組的反應
    echo = echo_agent()

    # 依據數量建立多個 Influencer
    influencer_agents = []
    for i in range(1, influencer_count + 1):
        output_key = "influencer" if influencer_count == 1 else f"influencer_{i}"
        influencer_agents.append(create_influencer_agent(index=i if influencer_count > 1 else None, output_key=output_key))

    sub_agents = [echo, *influencer_agents]

    # 視需求加入 Disrupter
    disrupter_output = "disrupter" if include_noise else "social_noise"
    sub_agents.append(create_disrupter_agent(output_key=disrupter_output))

    parallel_name = "social_noise_parallel" if include_noise else "social_parallel"
    return ParallelAgent(name=parallel_name, sub_agents=sub_agents)
