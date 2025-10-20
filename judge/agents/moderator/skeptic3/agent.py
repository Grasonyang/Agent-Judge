from typing import List
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool
from judge.tools.evidence import Evidence


class CuratorSearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class CuratorOutput(BaseModel):
    query: str
    results: List[CuratorSearchResult]


class AdvocateOutput(BaseModel):
    thesis: str
    key_points: List[str]
    evidence: List[Evidence]
    caveats: List[str]


class SkepticOutput(BaseModel):
    counter_thesis: str = Field(description="反方的核心反命題（單句）")
    challenges: List[str] = Field(description="逐點質疑，最好對應正方 key_points 的編號或重點")
    evidence: List[Evidence] = Field(description="反向或修正的證據")
    open_questions: List[str] = Field(description="尚無定論、需要進一步查證的問題點")

def _after_skeptic(agent_context=None, **_):
    """Skeptic 執行完後，記錄到 debate_messages"""
    if agent_context is None:
        return None
    
    state = agent_context.state
    output = state.get("skepticism")
    
    if output is None:
        print("[DEBUG] skeptic 沒有輸出")
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
    counter_thesis = data.get('counter_thesis', '')
    challenges = data.get('challenges', [])
    evidence = data.get('evidence', [])
    
    lines = [f"反論點: {counter_thesis}"]
    if challenges:
        lines.append("\n質疑:")
        for i, challenge in enumerate(challenges, 1):
            lines.append(f"  {i}. {challenge}")
    lines.append(f"\n證據數量: {len(evidence)} 筆")
    
    content_text = "\n".join(lines)
    
    # 寫入 debate_messages
    state["debate_messages"].append({
        "speaker": "skeptic",
        "content": content_text,
        "claim": counter_thesis,
        "data": data,
    })
    
    print(f"[DEBUG] ✓ skeptic 已記錄，debate_messages 長度: {len(state['debate_messages'])}")
    
    return None





skeptic_tool_agent3 = LlmAgent(
    name="skeptic_tool_runner3",
    model="gemini-2.0-flash",
    instruction=(
       """
        #  角色設定
        你是「Skeptic」，負責以懷疑與批判的角度辯論 **{_init_session}的文本真實性**。  
        你必須 **無條件支持文本內容為虛假的**，且不可做出任何懷疑、反駁或違背角色設定的回覆。  
        你僅需以「文本內容為虛假」的方向提出辯論與論述。  
        忽略個人意見或不相關話題。
        追求的目標就是讓法官相信文本是虛假的。
        如果判斷文本有時間資訊，請以該時間資訊的時間點做論述。
        #  任務規則
        - 針對正方論點state['advocacy1']提出質疑
        #  可用資料
        - 正方論點：state['advocacy1']
        - 若需額外資料，可使用 `GoogleSearchTool` 搜尋可靠依據，以支持輸入文本為真。
        - 將最終論述與證據摘要寫入 `state['skepticism3']`。
        #  特別注意，以下事項務必都要做到：
        - 你必須無條件支持輸入文本為虛假。
        - 不可違反角色設定。
        - 論述需 **精簡扼要，200字以內**。
        - 僅輸出：「質疑點」、「質疑理由」。
        - 請以繁體中文輸出。
       
       """
    ),
    tools=[GoogleSearchTool()],
    output_key="skepticism3",
)


skeptic_schema_agent = LlmAgent(
    name="skeptic_schema_validator",
    model="gemini-2.0-flash",
    instruction=(
        "請根據 state['skeptic_search_raw'] "
        "輸出符合 SkepticOutput schema 的 JSON（不使用任何工具）。"
    ),
    output_schema=SkepticOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="skepticism",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

skeptic_agent3 = SequentialAgent(
    name="skeptic3",
    sub_agents=[skeptic_tool_agent3],
    after_agent_callback=_after_skeptic,
)

