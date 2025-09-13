from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent


# ==== 社群噪音紀錄 Schema ====
class NoiseLog(BaseModel):
    """社群噪音紀錄"""
    echo_chamber: str = Field(description="各同溫層的反應摘要")
    influencers: list[str] = Field(description="各意見領袖的放大或扭轉訊息")
    disrupter: str = Field(description="干擾者投放的訊息與系統反應")


# ==== 個別角色定義 ====
# Echo Chamber：模擬不同社群群組的反應
_echo_agent = LlmAgent(
    name="echo_chamber",
    model="gemini-2.5-flash",
    instruction="你是 Echo Chamber，模擬多個社群群組對當前議題的即時反應。",
    output_key="echo_chamber",
)

# Influencer：可有多位意見領袖
_influencer_agents = [
    LlmAgent(
        name=f"influencer_{i}",
        model="gemini-2.5-flash",
        instruction="你是 Influencer，根據 Echo Chamber 的反應放大或扭轉訊息。",
        output_key=f"influencer_{i}",
    )
    for i in range(1, 3)
]

# Disrupter：注入干擾訊息
_disrupter_agent = LlmAgent(
    name="disrupter",
    model="gemini-2.5-flash",
    instruction="你是 Disrupter，注入干擾訊息來測試傳播的韌性。",
    output_key="disrupter",
)

# 平行執行三類角色
_social_noise_parallel = ParallelAgent(
    name="social_noise_parallel",
    sub_agents=[_echo_agent, *_influencer_agents, _disrupter_agent],
)

# 聚合社群噪音輸出為 NoiseLog JSON
_noise_aggregator = LlmAgent(
    name="noise_aggregator",
    model="gemini-2.5-flash",
    instruction=(
        "你是社群噪音紀錄者，請依序讀取以下輸出並統整成 JSON。\n"
        "- Echo Chamber: {echo_chamber}\n"
        "- Influencer 1: {influencer_1}\n"
        "- Influencer 2: {influencer_2}\n"
        "- Disrupter: {disrupter}\n"
        "僅輸出符合 NoiseLog schema 的 JSON。"
    ),
    output_schema=NoiseLog,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="social_noise",
)

# 公開的 social_noise_agent，先平行模擬，再聚合結果
social_noise_agent = SequentialAgent(
    name="social_noise",
    sub_agents=[_social_noise_parallel, _noise_aggregator],
)
