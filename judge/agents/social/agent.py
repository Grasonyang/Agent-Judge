from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent

from .base import create_social_agent


# ==== 社群擴散紀錄 Schema ====
class SocialLog(BaseModel):
    """社群擴散的整體紀錄"""
    echo_chamber: str = Field(description="各同溫層的反應摘要")
    influencer: str = Field(description="意見領袖如何放大或扭轉訊息")
    disrupter: str = Field(description="干擾者投放的訊息與系統反應")
    polarization_index: float = Field(description="0 到 1 之間的極化指數")
    virality_score: float = Field(description="0 到 1 之間的病毒式擴散分數")
    manipulation_risk: float = Field(description="0 到 1 之間的操弄風險")


# ==== 建立平行角色流程 ====
_social_parallel = create_social_agent(influencer_count=1, include_noise=False)

# 聚合社群輸出為 SocialLog JSON
_social_aggregator = LlmAgent(
    name="social_aggregator",
    model="gemini-2.5-flash",
    instruction=(
        "你是社群紀錄者，請依序讀取以下輸出並統整成 JSON。\n"
        "- Echo Chamber: {echo_chamber}\n"
        "- Influencer: {influencer}\n"
        "- Disrupter: {social_noise}\n"
        "請根據上述內容計算以下指標：\n"
        "polarization_index、virality_score、manipulation_risk，數值介於 0 到 1。\n"
        "僅輸出符合 SocialLog schema 的 JSON。"
    ),
    output_schema=SocialLog,
    # 禁止傳遞以符合 output_schema 規定
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="social_log",
)

# 公開的 social_summary_agent，先平行模擬，再聚合結果
social_summary_agent = SequentialAgent(
    name="social_summary",
    sub_agents=[_social_parallel, _social_aggregator],
)
