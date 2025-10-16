"""主持人相關工具：提供退出迴圈與統計指標"""

from typing import Any
from pydantic import BaseModel
from google.adk.tools.agent_tool import AgentTool

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
#from .advocate import advocate_agent
#from .skeptic import skeptic_agent
from .devil import devil_agent

LOG_MAP = {
    "call_advocate": ("advocate", "advocacy"),
    "call_skeptic": ("skeptic", "skepticism"),
    "call_devil": ("devil", "devil_turn"),
}


def exit_loop(tool_context):
    try:
        tool_context.actions.escalate = True
    except Exception:
        pass
    return {"ok": True}


def update_metrics(state):
    prev_points = state.get("prev_dispute_points", 0)
    curr_points = state.get("dispute_points", 0)
    state["delta_dispute_points"] = curr_points - prev_points
    state["prev_dispute_points"] = curr_points

    prev_cred = state.get("prev_credibility", 0.0)
    curr_cred = state.get("credibility", 0.0)
    state["delta_credibility"] = curr_cred - prev_cred
    state["prev_credibility"] = curr_cred

    prev_ev = state.get("prev_evidence_count", 0)
    curr_ev = len(state.get("evidence", []))
    state["new_evidence_gain"] = curr_ev - prev_ev
    state["prev_evidence_count"] = curr_ev


def should_stop(state) -> bool:
    return (
        state.get("delta_dispute_points", 0) <= 0
        or state.get("delta_credibility", 0) <= 0
        or state.get("new_evidence_gain", 0) <= 0
    )


def ensure_debate_messages(callback_context=None, **_):
    if callback_context is None:
        print("[DEBUG] ensure_debate_messages: callback_context is None")
        return None
    st = callback_context.state
    
    before_len = len(st.get("debate_messages", []))
    
    if "debate_messages" not in st or not isinstance(st.get("debate_messages"), list):
        st["debate_messages"] = []
        print(f"[DEBUG] ensure_debate_messages: 初始化 debate_messages")
    else:
        print(f"[DEBUG] ensure_debate_messages: debate_messages 已存在，長度 {before_len}")
    
    return None


def _summarize_payload(payload, speaker: str) -> str:
    try:
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump()
    except Exception:
        pass

    if isinstance(payload, dict):
        if speaker == "advocate":
            thesis = payload.get("thesis")
            points = payload.get("key_points") or []
            if thesis and isinstance(points, list):
                pts = "\n".join(f"- {p}" for p in points[:5])
                return f"Thesis: {thesis}\n{pts}".strip()
        if speaker == "skeptic":
            ct = payload.get("counter_thesis")
            ch = payload.get("challenges") or []
            if ct and isinstance(ch, list):
                pts = "\n".join(f"- {p}" for p in ch[:5])
                return f"Counter-thesis: {ct}\n{pts}".strip()
        if speaker == "devil":
            stance = payload.get("stance")
            atk = payload.get("attack_points") or []
            if stance and isinstance(atk, list):
                pts = "\n".join(f"- {p}" for p in atk[:5])
                return f"Stance: {stance}\n{pts}".strip()
    # fallback to string
    return str(payload)
def format_debate_content(output, speaker: str) -> str:
    """將 agent 輸出格式化為可讀的辯論內容"""
    try:
        # 轉換為字典
        if hasattr(output, 'model_dump'):
            data = output.model_dump()
        elif isinstance(output, dict):
            data = output
        else:
            return str(output)
        
        lines = []
        
        if speaker == "advocate":
            thesis = data.get('thesis', '')
            key_points = data.get('key_points', [])
            evidence = data.get('evidence', [])
            
            lines.append(f"論點: {thesis}")
            if key_points:
                lines.append("\n支持理由:")
                for i, point in enumerate(key_points, 1):
                    lines.append(f"  {i}. {point}")
            lines.append(f"\n證據數量: {len(evidence)} 筆")
        
        elif speaker == "skeptic":
            counter_thesis = data.get('counter_thesis', '')
            challenges = data.get('challenges', [])
            evidence = data.get('evidence', [])
            
            lines.append(f"反論點: {counter_thesis}")
            if challenges:
                lines.append("\n質疑:")
                for i, challenge in enumerate(challenges, 1):
                    lines.append(f"  {i}. {challenge}")
            lines.append(f"\n證據數量: {len(evidence)} 筆")
        
        elif speaker == "devil":
            stance = data.get('stance', '')
            attack_points = data.get('attack_points', [])
            evidence = data.get('evidence', [])
            
            lines.append(f"極端質疑: {stance}")
            if attack_points:
                lines.append("\n攻擊點:")
                for i, attack in enumerate(attack_points, 1):
                    lines.append(f"  {i}. {attack}")
            lines.append(f"\n證據數量: {len(evidence)} 筆")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"[格式化錯誤: {e}]"


def extract_main_claim(output, speaker: str) -> str:
    """提取核心主張"""
    try:
        if hasattr(output, 'model_dump'):
            data = output.model_dump()
        elif isinstance(output, dict):
            data = output
        else:
            return ""
        
        if speaker == "advocate":
            return data.get('thesis', '')
        elif speaker == "skeptic":
            return data.get('counter_thesis', '')
        elif speaker == "devil":
            return data.get('stance', '')
        
        return ""
    except Exception:
        return ""


async def log_tool_output(tool, args=None, tool_context=None, tool_response=None, result=None, append_event=None, **_):
    print(f"\n{'='*60}")
    print(f"[DEBUG] log_tool_output 被呼叫")
    print(f"  工具: {tool.name}")
    print(f"  tool_context 存在: {tool_context is not None}")
    
    if tool_context:
        print(f"  state keys: {list(tool_context.state.keys())}")
        print(f"  debate_messages 長度: {len(tool_context.state.get('debate_messages', []))}")
    
    response = tool_response if tool_response is not None else result
    info = LOG_MAP.get(tool.name)
    
    print(f"  在 LOG_MAP 中: {info is not None}")
    
    if info:
        speaker, key = info
        st = tool_context.state if tool_context is not None else {}
        output = st.get(key)
        
        print(f"  speaker: {speaker}, key: {key}")
        print(f"  state['{key}'] 存在: {output is not None}")
        
        if output is not None:
            # ... 原有邏輯 ...
            st["debate_messages"].append({...})
            print(f"  ✓ 成功寫入，目前長度: {len(st['debate_messages'])}")
        else:
            print(f"  ✗ state['{key}'] 不存在，無法寫入")
    else:
        print(f"  ✗ 工具不在 LOG_MAP，跳過")
    
    print(f"{'='*60}\n")
    return response


#advocate_tool = AgentTool(advocate_agent)
#advocate_tool.name = "call_advocate"
#skeptic_tool = AgentTool(skeptic_agent)
#skeptic_tool.name = "call_skeptic"
#devil_tool = AgentTool(devil_agent)
#devil_tool.name = "call_devil"


class NextTurnDecision(BaseModel):
    next_speaker: str
    rationale: str
