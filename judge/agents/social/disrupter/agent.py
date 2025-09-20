from google.adk.agents import LlmAgent


def create_disrupter_agent(output_key: str) -> LlmAgent:
    return LlmAgent(
        name="disrupter",
        model="gemini-2.5-flash",
        instruction="你是 Disrupter，注入干擾訊息來測試傳播的韌性。",
        output_key=output_key,
    )


__all__ = ["create_disrupter_agent"]

