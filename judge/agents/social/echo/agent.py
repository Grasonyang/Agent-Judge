from google.adk.agents import LlmAgent


def echo_agent() -> LlmAgent:
    return LlmAgent(
        name="echo_chamber",
        model="gemini-2.5-flash",
        instruction="你是 Echo Chamber，模擬多個社群群組對當前議題的即時反應，請提供摘要，並且精簡輸出，僅保留重點。",
        output_key="echo_chamber",
    )


__all__ = ["echo_agent"]

