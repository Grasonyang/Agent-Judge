"""
Debate Logger Agent - 在辯論結束後整理並記錄完整的辯論內容

職責：
1. 收集 advocacy、skepticism、devil_turn
2. 寫入 state['debate_messages'] 和 state['debate_log']
3. 供後續 agent（如 Jury）使用
"""

from google.adk.agents import LlmAgent


def _collect_and_log_debate(callback_context=None, **_):
    """在 agent 執行前，從 state 收集辯論內容並寫入 debate_messages"""
    if callback_context is None:
        return None
    
    state = callback_context.state
    
    # 初始化
    if "debate_messages" not in state:
        state["debate_messages"] = []
    
    if "debate_log" not in state:
        state["debate_log"] = []
    
    debate_messages = []
    
    print("\n[DEBUG] 開始整理辯論紀錄...")
    
    # 1. 收集正方
    if 'advocacy' in state:
        advocacy = state['advocacy']
        if hasattr(advocacy, 'model_dump'):
            advocacy = advocacy.model_dump()
        
        thesis = advocacy.get('thesis', '')
        key_points = advocacy.get('key_points', [])
        evidence = advocacy.get('evidence', [])
        
        # 格式化內容
        content_lines = [f"論點: {thesis}"]
        if key_points:
            content_lines.append("\n支持理由:")
            for i, point in enumerate(key_points, 1):
                content_lines.append(f"  {i}. {point}")
        content_lines.append(f"\n證據數量: {len(evidence)} 筆")
        
        debate_messages.append({
            "speaker": "advocate",
            "content": "\n".join(content_lines),
            "claim": thesis,
            "data": advocacy,
        })
        
        print(f"  ✓ 已收集 advocate")
    
    # 2. 收集反方
    if 'skepticism' in state:
        skepticism = state['skepticism']
        if hasattr(skepticism, 'model_dump'):
            skepticism = skepticism.model_dump()
        
        counter_thesis = skepticism.get('counter_thesis', '')
        challenges = skepticism.get('challenges', [])
        evidence = skepticism.get('evidence', [])
        
        content_lines = [f"反論點: {counter_thesis}"]
        if challenges:
            content_lines.append("\n質疑:")
            for i, challenge in enumerate(challenges, 1):
                content_lines.append(f"  {i}. {challenge}")
        content_lines.append(f"\n證據數量: {len(evidence)} 筆")
        
        debate_messages.append({
            "speaker": "skeptic",
            "content": "\n".join(content_lines),
            "claim": counter_thesis,
            "data": skepticism,
        })
        
        print(f"  ✓ 已收集 skeptic")
    
    # 3. 收集極端質疑
    if 'devil_turn' in state:
        devil = state['devil_turn']
        if hasattr(devil, 'model_dump'):
            devil = devil.model_dump()
        
        stance = devil.get('stance', '')
        attack_points = devil.get('attack_points', [])
        evidence = devil.get('evidence', [])
        
        content_lines = [f"極端質疑: {stance}"]
        if attack_points:
            content_lines.append("\n攻擊點:")
            for i, attack in enumerate(attack_points, 1):
                content_lines.append(f"  {i}. {attack}")
        content_lines.append(f"\n證據數量: {len(evidence)} 筆")
        
        debate_messages.append({
            "speaker": "devil",
            "content": "\n".join(content_lines),
            "claim": stance,
            "data": devil,
        })
        
        print(f"  ✓ 已收集 devil")
    
    # 寫入 state
    state["debate_messages"] = debate_messages
    
    # 同時建立 debate_log（Turn 格式）
    from judge.tools.debate_log import Turn
    
    debate_log = []
    for msg in debate_messages:
        turn = Turn(
            speaker=msg["speaker"],
            content=msg["content"],
            claim=msg.get("claim"),
            confidence=None,
            evidence=msg.get("data", {}).get("evidence", []),
            fallacies=[],
        )
        debate_log.append(turn)
    
    state["debate_log"] = debate_log
    
    print(f"[DEBUG] 辯論紀錄整理完成:")
    print(f"  - debate_messages 長度: {len(state['debate_messages'])}")
    print(f"  - debate_log 長度: {len(state['debate_log'])}")
    
    return None


debate_agent = LlmAgent(
    name="debate_logger2",
    model="gemini-2.5-flash",
    instruction=(
        "你是辯論紀錄員。你的任務已經在 before_agent_callback 中完成，"
        "此處只需回傳一個簡短確認訊息。"
    ),
    before_agent_callback=_collect_and_log_debate,
    output_key="debate_logger_status",
)