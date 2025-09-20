from typing import Optional
from google.adk.agents import LlmAgent


def create_influencer_agent(index: Optional[int] = None, output_key: Optional[str] = None) -> LlmAgent:
    name = f"influencer_{index}" if index else "influencer"
    out_key = output_key or ("influencer" if not index else f"influencer_{index}")
    return LlmAgent(
        name=name,
        model="gemini-2.5-flash",
        instruction="你是 Influencer，根據 Echo Chamber 的反應放大或扭轉訊息。",
        output_key=out_key,
    )


__all__ = ["create_influencer_agent"]

