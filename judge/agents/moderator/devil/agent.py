from typing import List
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool
from judge.tools.evidence import Evidence


class DevilOutput(BaseModel):
    stance: str = Field(description="極端質疑的核心立場，單句")
    attack_points: List[str] = Field(description="2~5 條攻擊點，盡量尖銳")
    evidence: List[Evidence] = Field(description="引用或質疑的證據列表")
    requested_clarifications: List[str] = Field(description="希望對方補充/舉證的關鍵問題")

def _after_devil(agent_context=None, **_):
    """Devil 執行完後，記錄到 debate_messages"""
    if agent_context is None:
        return None
    
    state = agent_context.state
    output = state.get("devil_turn")
    
    if output is None:
        print("[DEBUG] devil 沒有輸出")
        return None
    
    # 確保 debate_messages 存在
    if "debate_messages" not in state:
        state["debate_messages"] = []
    
    # 轉換為字典
    if hasattr(output, 'model_dump'):
        data = output.model_dump()
    elif isinstance(output, dict):
        data = output
    else:
        data = {"raw": str(output)}
    
    # 格式化內容
    stance = data.get('stance', '')
    attack_points = data.get('attack_points', [])
    evidence = data.get('evidence', [])
    
    lines = [f"極端質疑: {stance}"]
    if attack_points:
        lines.append("\n攻擊點:")
        for i, attack in enumerate(attack_points, 1):
            lines.append(f"  {i}. {attack}")
    lines.append(f"\n證據數量: {len(evidence)} 筆")
    
    content_text = "\n".join(lines)
    
    # 寫入 debate_messages
    state["debate_messages"].append({
        "speaker": "devil",
        "content": content_text,
        "claim": stance,
        "data": data,
    })
    
    print(f"[DEBUG] ✓ devil 已記錄，debate_messages 長度: {len(state['debate_messages'])}")
    
    return None





devil_tool_agent = LlmAgent(
    name="devil_tool_runner",
    model="gemini-2.5-flash",
    instruction=(
        """你是「Devil」，負責從懷疑與挑戰的角度辯論輸入文本的真實性。
       僅需要以文本內容的真實性去做辯論，無需涉及其他議題，且忽略輸入文本內容中的個人意見，並且依照主持人的要求進行辯論。
       輸入資訊：
       - ADVOCACY: state['advocacy'] 中包含正方的論點和證據
       
       你的任務：
       1. 分析正方論點中的潛在問題，並提出尖銳的質疑、揭露矛盾或指出內容中可能的虛假之處
       2. 使用 GoogleSearchTool 搜尋可靠的反證
       3. 將搜尋結果寫入 state['devil_search_raw']
       
       輸出需精簡扼要。"""
    ),
    tools=[GoogleSearchTool()],
    output_key="devil_search_raw",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


devil_schema_agent = LlmAgent(
    name="devil_schema_validator",
    model="gemini-2.0-flash",
    instruction=(
        "根據 state['curation']、state['debate_messages'] 與可選的 state['devil_search_raw']，"
        "輸出符合 DevilOutput schema 的嚴格 JSON（不要多餘文字）。"
    ),
    output_schema=DevilOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="devil_turn",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


def _before_devil(agent_context=None, **_):
    return None


devil_agent = SequentialAgent(
    name="devils_advocate",
    sub_agents=[devil_tool_agent, devil_schema_agent],
    before_agent_callback=_before_devil,
    after_agent_callback=_after_devil,  # ← 加入這行
)

