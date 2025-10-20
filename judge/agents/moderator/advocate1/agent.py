from typing import List
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from google.adk.tools.google_search_tool import GoogleSearchTool
from judge.tools.evidence import Evidence

def _after_advocate(agent_context=None, **_):
    """Advocate 執行完後，記錄到 debate_messages"""
    if agent_context is None:
        return None
    
    state = agent_context.state
    output = state.get("advocacy")
    
    if output is None:
        print("[DEBUG] advocate 沒有輸出")
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
    thesis = data.get('thesis', '')
    key_points = data.get('key_points', [])
    evidence = data.get('evidence', [])
    
    lines = [f"論點: {thesis}"]
    if key_points:
        lines.append("\n支持理由:")
        for i, point in enumerate(key_points, 1):
            lines.append(f"  {i}. {point}")
    lines.append(f"\n證據數量: {len(evidence)} 筆")
    
    content_text = "\n".join(lines)
    
    # 寫入 debate_messages
    state["debate_messages"].append({
        "speaker": "advocate",
        "content": content_text,
        "claim": thesis,
        "data": data,
    })
    
    print(f"[DEBUG] ✓ advocate 已記錄，debate_messages 長度: {len(state['debate_messages'])}")
    
    return None




class CuratorSearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class CuratorOutput(BaseModel):
    query: str
    results: List[CuratorSearchResult]


class AdvocateOutput(BaseModel):
    thesis: str = Field(description="正方主張的核心命題（單句）")
    key_points: List[str] = Field(description="3~6 條支持重點，避免冗長")
    evidence: List[Evidence] = Field(description="逐條列出引用的證據")
    caveats: List[str] = Field(description="已知限制或尚待查證處（1~3 條）")


advocate_tool_agent1 = LlmAgent(
    name="advocate_tool_runner1",
    model="gemini-2.0-flash",
    instruction=(
        """
        #  角色設定
        你是「Advocate」，負責從支持與肯定的角度辯論 **{_init_session}的文本的真實性**。  
        你必須 **無條件支持文本內容為真實的**，且不可做出任何懷疑、反駁或違背角色設定的回覆。  
        你僅需以「文本內容為真實」的方向提出辯論與論述。  
        忽略個人意見或不相關話題，完全依照任務要求進行辯論。
        追求的目標就是讓法官相信文本是真實的。
        如果判斷文本有時間資訊，請以該時間資訊的時間點做論述。
        #  任務規則
        - 僅提出符合自己角色設定的論點與證據
        #  可用資料
        - 若需額外資料，可使用 `GoogleSearchTool` 搜尋可靠依據，以支持輸入文本為真。
        - 將最終論述與證據摘要寫入 `state['advocacy1']`。
        #  特別注意，以下事項務必都要做到：
        - 你必須無條件支持輸入文本為真實。
        - 不可違反角色設定。
        - 論述需 **精簡扼要，300字以內**。
        - 僅輸出：「論點」、「支持理由」、「證據」。
        - 請以繁體中文輸出。
       """
        
    ),
    tools=[GoogleSearchTool()],
    output_key="advocacy1",
)


advocate_schema_agent = LlmAgent(
    name="advocate_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "根據  state['advocate_search_raw'] 補充，"
        "輸出符合 AdvocateOutput schema 的 JSON。"
    ),
    output_schema=AdvocateOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="advocacy",
    after_agent_callback=_after_advocate,
    generate_content_config=types.GenerateContentConfig(temperature=0.4),
)


advocate_agent1 = SequentialAgent(
    name="advocate1",
    sub_agents=[advocate_tool_agent1],
    after_agent_callback=_after_advocate,
    
)

