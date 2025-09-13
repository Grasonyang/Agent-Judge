from google.adk.agents import LlmAgent, ParallelAgent


def create_social_agent(influencer_count: int, include_noise: bool) -> ParallelAgent:
    """建立社群擴散的基礎流程

    Args:
        influencer_count: 意見領袖的數量
        include_noise: 是否紀錄噪音輸出
    """
    # Echo Chamber：模擬不同社群群組的反應
    echo_agent = LlmAgent(
        name="echo_chamber",
        model="gemini-2.5-flash",
        instruction="你是 Echo Chamber，模擬多個社群群組對當前議題的即時反應，請提供摘要。",
        output_key="echo_chamber",
    )

    # 依據數量建立多個 Influencer
    influencer_agents = []
    for i in range(1, influencer_count + 1):
        output_key = "influencer" if influencer_count == 1 else f"influencer_{i}"
        influencer_agents.append(
            LlmAgent(
                name=f"influencer_{i}" if influencer_count > 1 else "influencer",
                model="gemini-2.5-flash",
                instruction="你是 Influencer，根據 Echo Chamber 的反應放大或扭轉訊息。",
                output_key=output_key,
            )
        )

    sub_agents = [echo_agent, *influencer_agents]

    # 視需求加入 Disrupter
    disrupter_output = "disrupter" if include_noise else "social_noise"
    disrupter_agent = LlmAgent(
        name="disrupter",
        model="gemini-2.5-flash",
        instruction="你是 Disrupter，注入干擾訊息來測試傳播的韌性。",
        output_key=disrupter_output,
    )
    sub_agents.append(disrupter_agent)

    parallel_name = "social_noise_parallel" if include_noise else "social_parallel"
    return ParallelAgent(name=parallel_name, sub_agents=sub_agents)
