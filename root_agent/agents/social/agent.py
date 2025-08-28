from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent


# ==== 社群擴散紀錄 Schema ====
class SocialLog(BaseModel):
    """社群擴散的整體紀錄"""
    echo_chamber: str = Field(description="各同溫層的反應摘要")
    influencer: str = Field(description="意見領袖如何放大或扭轉訊息")
    disrupter: str = Field(description="干擾者投放的訊息與系統反應")


# ==== 個別角色定義 ====
# Echo Chamber：模擬不同社群群組的反應
_echo_agent = LlmAgent(
    name="echo_chamber",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Echo Chamber，模擬多個社群群組對當前議題的即時反應，"
        "請提供摘要。"
    ),
    output_key="echo_chamber",
)

# Influencer：放大或扭轉 Echo Chamber 產生的內容
_influencer_agent = LlmAgent(
    name="influencer",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Influencer，根據 Echo Chamber 的反應放大或扭轉訊息。"
    ),
    output_key="influencer",
)

# Disrupter：注入干擾訊息以測試傳播韌性
_disrupter_agent = LlmAgent(
    name="disrupter",
    model="gemini-2.5-flash",
    instruction=(
        "你是 Disrupter，注入干擾訊息來測試傳播的韌性。"
    ),
    output_key="disrupter",
)

# 平行模擬三種角色
_social_parallel = ParallelAgent(
    name="social_parallel",
    sub_agents=[_echo_agent, _influencer_agent, _disrupter_agent],
)

# 聚合社群輸出為 SocialLog JSON
_social_aggregator = LlmAgent(
    name="social_aggregator",
    model="gemini-2.5-flash",
    instruction=(
        "你是社群紀錄者，請依序讀取以下輸出並統整成 JSON。\n"
        "- Echo Chamber: {echo_chamber}\n"
        "- Influencer: {influencer}\n"
        "- Disrupter: {disrupter}\n"
        "僅輸出符合 SocialLog schema 的 JSON。"
    ),
    output_schema=SocialLog,
    output_key="social_log",
)

# 公開的 social_agent，先平行模擬，再聚合結果
social_agent = SequentialAgent(
    name="social",
    sub_agents=[_social_parallel, _social_aggregator],
)
