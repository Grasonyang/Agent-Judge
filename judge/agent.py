from __future__ import annotations

from functools import partial
#把涵式專門化

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.sessions.session import Session
from google.genai import types

from judge.tools.session_service import session_service
from judge.agents.llm.agent import dynamic_fact_check

from judge.agents.knowledge.curator import curator_agent
from judge.agents.moderator.devil.agent import devil_agent
from judge.agents.adjudication.agent import adjudication_agent
from judge.agents.adjudication.evidence import evidence_agent
from judge.agents.adjudication.jury import jury_agent
from judge.agents.adjudication.synthesizer.agent import synthesizer_agent
from judge.agents.knowledge.historian import historian_agent
from judge.agents.moderator.agent import orchestrator_agent
from judge.agents.moderator.tools import log_tool_output

from judge.agents.social.agent import social_summary_agent
from judge.agents.social.noise.agent import social_noise_agent
from judge.agents.llm.agent import fact_check_agent
from judge.agents.classifier.agent import classifier_agent
from judge.agents.weight.agent import weight_agent
from judge.agents.debatelog.agent import debate_agent
from judge.tools import _before_init_session, append_event, make_record_callback


def create_session(state: dict | None = None) -> Session:
    """建立新的 Session（同步呼叫版）"""
    default_state = {
        "debate_messages": [],
        "agents": [],
        # 兩輪辯論的設定
        "debate_turn": 0,
        "current_round": 1,
        "current_phase": "statement",  # statement 或 challenge
    }
    
    # 合併使用者提供的 state
    if state:
        default_state.update(state)

    # 使用 google.adk 提供的同步 API，避免在此處建立事件迴圈
    return session_service.create_session_sync(
        app_name="agent_judge",
        user_id="user",
        state=default_state,
    )


def bind_session(session: Session) -> None:
    """將 append_event 函式注入各代理，避免全域依賴"""

    append_event_fn = partial(append_event, session, service=session_service)

    # 統一列出需要寫入事件的代理與對應鍵值
    # ← 把 advocate、skeptic、devil 從這裡移除！
    agent_event_map = [
        (curator_agent, "curator", "curation", False),
        (historian_agent, "historian", "history", False),
        (social_summary_agent, "social", "social_log", False),
        (evidence_agent, "evidence", "evidence", False),
        (jury_agent, "jury", "jury_result", True),
        (synthesizer_agent, "synthesizer", "final_report_json", True),
        # === 移除這三行 ===
        # (advocate_agent, "advocate", "advocacy", False),
        # (skeptic_agent, "skeptic", "skepticism", False),
        # (devil_agent, "devil", "devil_turn", False),
        (social_noise_agent, "social_noise", "social_noise", False),
    ]

    # 迴圈設定 after_agent_callback
    for agent, author, key, show_pretty in agent_event_map:
        agent.after_agent_callback = partial(
            make_record_callback(author, key, show_pretty_message=show_pretty),
            append_event=append_event_fn
        )

# 建立一個包裝 Agent,在執行前先調用動態查核
llm_wrapper_agent = LlmAgent(
    name="llm_wrapper",
    model="gemini-2.5-flash",
    instruction=(
        "你是 LLM 層的協調者。\n"
        "state 中已經包含了假新聞查核的結果:\n"
        "- text_classification: 新聞類別\n"
        "- fact_check_result: 查核結果\n"
        "- fact_check_result_json: 格式化的查核結果\n\n"
        "請確認這些結果已正確儲存到 state 中。"
    ),
    output_key="llm_layer_status",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)


# 建立自訂的 before_callback,在執行前先執行動態查核
async def _before_llm_layer(agent_context=None, **_):
    """在 LLM 層執行前,先執行動態查核"""
    if agent_context is None:
        return None
    
    state = agent_context.state
    news_text = state.get("_init_session", "")
    
    if news_text:
        print("\n" + "=" * 70)
        print("執行動態假新聞查核...")
        print("=" * 70)
        
        # 執行動態查核
        try:
            result = await dynamic_fact_check.run_async(news_text, agent_context)
            
            # 結果已經自動存到 state 中了
            print("\n✅ 動態查核完成,結果已存到 state\n")
        except Exception as e:
            print(f"\n❌ 動態查核失敗: {e}\n")
    
    return None


# 設置 before_callback
llm_wrapper_agent.before_agent_callback = _before_llm_layer

# =============== Root Pipeline ===============
# 固定順序：Curator → Historian → 主持人回合制（正/反/極端）→ Social → Evidence → Jury → Synthesizer(JSON)

init_session = LlmAgent(
    name="init_session",
    model="gemini-2.0-flash",
    instruction=("初始化 session（此代理僅用於在執行前設定 state）。"
                 "請把接收到的資訊做提煉，使輸入文本僅保留事實的描述及事情發生的時間，移除個人意見內容，限200字內。"
                 "注意切勿自行該改文本內容，請真實以輸入文本內容作呈現"
                 "將結果存入 state['_init_session'] 中。"
                 ),
    before_agent_callback=_before_init_session,
    output_key="_init_session",
)

root_agent = SequentialAgent(
    name="root_pipeline",
    sub_agents=[
        init_session,
        llm_wrapper_agent,
    ],
)


if __name__ == "__main__":
    session = create_session()
    bind_session(session)
    # 如需執行 root_agent，請自行呼叫對應方法
