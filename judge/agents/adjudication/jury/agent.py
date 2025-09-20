from typing import List
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent,SequentialAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
import json
from google.genai import types
from judge.tools import flatten_fallacies
from ckip_transformers.nlp import CkipWordSegmenter, CkipPosTagger, CkipNerChunker
import numpy as np
import re



# 初始化 CKIP 工具
ws_driver = CkipWordSegmenter(model="bert-base")
pos_driver = CkipPosTagger(model="bert-base")
ner_driver = CkipNerChunker(model="bert-base")

# 修正：FUZZY_WORDS 中有重複的鍵值
FUZZY_WORDS = {
    # 正向詞彙（支持「為真」）
    "真實": {"direction": "pos", "score": 0.751311380443692},
    "正確": {"direction": "pos", "score": 0.9366013546832714},
    "成立": {"direction": "pos", "score": 0.9366013546832714},
    "成立的": {"direction": "pos", "score": 0.9366013546832714},
    "的確": {"direction": "pos", "score": 0.6},
    "一致": {"direction": "pos", "score": 0.8},
    "吻合": {"direction": "pos", "score": 0.8},
    "對的": {"direction": "pos", "score": 0.7463066940858591},
    "屬實": {"direction": "pos", "score": 0.922994846547313},
    "科學證據": {"direction": "pos", "score": 0.8},
    "科學": {"direction": "pos", "score": 0.8},
    "根據": {"direction": "pos", "score": 0.8},
    "科學根據": {"direction": "pos", "score": 0.8},
    "新聞": {"direction": "pos", "score": 0.868975062193891},
    "新聞來源": {"direction": "pos", "score": 0.868975062193891},
    "研究": {"direction": "pos", "score": 0.868975062193891},
    "證據": {"direction": "pos", "score": 0.8628936965177872},
    "佐證": {"direction": "pos", "score": 0.8352132004104946},  # 修正：移除重複但數值不同的佐證
    "證實": {"direction": "pos", "score": 0.5807936899622632},
    "相符": {"direction": "pos", "score": 0.9459154551052427},
    "符合": {"direction": "pos", "score": 0.7},
    "適用": {"direction": "pos", "score": 0.7},
    "可以": {"direction": "pos", "score": 0.6},
    "保證": {"direction": "pos", "score": 0.6},
    "精確": {"direction": "pos", "score": 0.7206822418072106},
    "確認": {"direction": "pos", "score": 0.7883985575039467},
    "確實": {"direction": "pos", "score": 0.7},
    "確定": {"direction": "pos", "score": 0.6},
    "反映": {"direction": "pos", "score": 0.6},
    "準確": {"direction": "pos", "score": 0.6654316248679483},
    "資料": {"direction": "pos", "score": 0.7814497886822308},
    "明確": {"direction": "pos", "score": 0.7224219803918052},
    "充分": {"direction": "pos", "score": 0.8333342721669755},
    "道理": {"direction": "pos", "score": 0.6501229503281717},
    "合理": {"direction": "pos", "score": 0.706866041237471},
    "找到": {"direction": "pos", "score": 0.6151630595756533},
    "足夠": {"direction": "pos", "score": 0.4825235353822853},
    "有效": {"direction": "pos", "score": 0.7},
    "關聯": {"direction": "pos", "score": 0.7},
    "等同": {"direction": "pos", "score": 0.7},
    "案例": {"direction": "pos", "score": 0.2},
    
    # 負向詞彙（支持「為假」）
    "錯誤": {"direction": "neg", "score": 0.8744036171585566},
    "詐騙": {"direction": "neg", "score": 0.7},
    "虛假": {"direction": "neg", "score": 0.9},
    "不實": {"direction": "neg", "score": 0.8},
    "騙取": {"direction": "neg", "score": 0.9},
    "造假": {"direction": "neg", "score": 0.6517545450444481},
    "假": {"direction": "neg", "score": 0.8},
    "假的": {"direction": "neg", "score": 0.8},
    "是假的": {"direction": "neg", "score": 0.8},
    "偽造": {"direction": "neg", "score": 0.76711673818182},
    "爭議": {"direction": "neg", "score": 0.8988146569746402},
    "誇張": {"direction": "neg", "score": 0.6857988054750036},
    "誇大": {"direction": "neg", "score": 0.7501742135582994},
    "評估": {"direction": "neg", "score": 0.586},
    "誤導": {"direction": "neg", "score": 0.586},  # 修正：移除重複的誤導
    "謠言": {"direction": "neg", "score": 0.8},
    "不宜": {"direction": "neg", "score": 0.7},
    "不建議": {"direction": "neg", "score": 0.7},
    "過時": {"direction": "neg", "score": 0.635},
    "不符": {"direction": "neg", "score": 0.8744036171585566},
    "不足": {"direction": "neg", "score": 0.586},
    "矛盾": {"direction": "neg", "score": 0.3},
    "無關": {"direction": "neg", "score": 0.6},
    "誤導性": {"direction": "neg", "score": 0.8},
    "無稽之談": {"direction": "neg", "score": 0.8},
    "違反": {"direction": "neg", "score": 0.6},
    "而非": {"direction": "neg", "score": 0.7},
}

ADVERBS = {
    # 強化類（倍率 < 1）
    "極": 1/3, "至": 1/3, "至上": 1/3, "整個": 1/3, "整體": 1/3, "一切": 1/3,
    "充滿": 1/3, "整": 1/3, "最": 1/3, "極度": 1/3, "完全": 1/3, "具體": 1/3, "足夠": 1/3,

    "非常": 1/2, "特別": 1/2, "格外": 1/2, "尤其": 1/2, "遠遠": 1/2, "可靠": 1/2,

    "眾多": 1/1.6, "大多": 1/1.6, "大多數": 1/1.6, "大幅": 1/1.6,
    "大量": 1/1.6, "大都": 1/1.6, "大部分": 1/1.6, "致": 1/1.6,
    "大致": 1/1.6, "基本": 1/1.6, "充分": 1/1.6,

    "許多": 1/1.4, "更加": 1/1.4, "多數": 1/1.4, "多量": 1/1.4,
    "更": 1/1.4, "越": 1/1.4, "愈": 1/1.4, "經常": 1/1.4,
    "通常": 1/1.4, "常常": 1/1.4, "常": 1/1.4, "一向": 1/1.4,
    "時常": 1/1.4, "時時": 1/1.4, "很": 1/1.4, "有": 1/1.4, "宜": 1/1.4,

    "多於": 1/1.2, "超出": 1/1.2, "過": 1/1.2, "多點": 1/1.2, "較": 1/1.2,

    "越來越": 1.2, "愈來愈": 1.2, "之上": 1.2, "更加": 1.2,  # 修正：移除重複的更加

    # 中等增強
    "還有": 1.4, "不少": 1.4, "幾乎": 1.4, "漸漸": 1.4,
    "逐漸": 1.4, "漸進": 1.4, "每每不全": 1.4,

    # 中性
    "中等": 1.6, "居中": 1.6, "一半": 1.6,

    # 減弱（倍率 > 1）
    "多少": 2, "差不多": 2, "多多少少": 2, "一時": 2,
    "一會兒": 2, "大約": 2, "大概": 2, "僅僅一些": 2,
    "可能": 2, "部分": 2,

    "有時": 2.4, "偶然": 2.4, "一下子": 2.4,
    "短暫": 2.4, "存在": 2.4, "進一步": 2.4,

    "輕微": 3, "稍微": 3, "稍稍": 3, "略": 3, "略顯": 3,
    "較為": 3, "過於": 3,

    "一點": 3.2, "一點點": 3.2, "有點": 3.2, "一些": 3.2, "某些": 3.2,

    "少數": 3.4, "少許": 3.4, "稀少": 3.4, "少量": 3.4, "不太": 3.4,
}

# 否定詞列表
NEGATIONS = ["不", "不是", "並非", "沒有", "缺乏", "無", "非", "無法", "並未", "未", "未經", "毫無", "有限", "不會"]

# 視為斷開的詞性
BREAK_POS = {"P", "C", "Caa", "Cab", "Cba", "Cbb", "T"}   # P=介係詞, Cxx=連接詞, T=語助詞 


def calculate_fuzzy_score(state_data: str = "", debug: bool = True) -> dict:
    """
    計算句子的模糊詞分數（考慮副詞與否定詞）
    
    Args:
        state_data: JSON 字符串，包含 fact_check_result_json
        debug: 是否輸出調試信息
    
    Returns:
        dict: 包含 final_score, result 和可能的 error（不包含 NaN 值）
    """
    try:
        # 修正：處理不同的輸入格式
        if state_data and state_data.strip():
            try:
                # 先嘗試解析 JSON
                parsed_data = json.loads(state_data)
                
                # 檢查是否有嵌套的 jury_result
                if "jury_result" in parsed_data:
                    llm_result = parsed_data.get("jury_result")
                    # 如果 llm_result 是字符串，再解析一次
                    if isinstance(llm_result, str):
                        llm_data = json.loads(llm_result)
                    else:
                        llm_data = llm_result
                # 否則直接使用解析的數據（可能直接包含 analysis 和 classification）
                elif "verdict" in parsed_data:
                    llm_data = parsed_data
                else:
                    if debug:
                        print("錯誤：未找到預期的數據結構")
                    return {"final_score": 0.0, "result": "unknown", "error": "Invalid data structure"}
                
            except json.JSONDecodeError as e:
                if debug:
                    print(f"JSON 解析錯誤: {e}")
                return {"final_score": 0.0, "result": "unknown", "error": f"JSON parse error: {e}"}
        else:
            if debug:
                print("警告：未提供有效的 state_data")
            return {"final_score": 0.0, "result": "unknown", "error": "No state_data provided"}

        # 獲取分析文本
        sentence = llm_data.get("verdict", "")
        if not sentence:
            if debug:
                print("錯誤：未找到 verdict 欄位")
                print("可用的鍵值:", list(llm_data.keys()) if isinstance(llm_data, dict) else "數據不是字典格式")
            return {"final_score": 0.0, "result": "unknown", "error": "No analysis field found"}

        # 進行斷詞和詞性標注
        try:
            words_list = ws_driver([sentence])
            words = words_list[0]
            pos_list = pos_driver([words])[0]
        except Exception as e:
            if debug:
                print(f"斷詞或詞性標注錯誤: {e}")
            return {"final_score": 0.0, "result": "unknown", "error": f"Segmentation error: {e}"}

        if debug:
            print("斷詞結果:", words)
            print("詞性結果:", pos_list)

        final_score = 0.0
        count_word = 0
        matched_indices = set()

        def check_negation(i):
            """檢查目標詞前後的否定詞"""
            neg_count = 0
            # 往前檢查
            for j in range(i - 1, max(i - 6, -1), -1):
                if j < 0 or j >= len(words):  # 修正：添加邊界檢查
                    continue
                if re.match(r"^[「。！？,.!?、；;，」]$", words[j]):
                    break
                if words[j] in NEGATIONS:
                    neg_count += 1
                    if debug:
                        print(f"  -> 目標詞 {words[i]} 前方找到否定詞: {words[j]} (index={j})")
            
            # 往後檢查
            for j in range(i + 1, min(i + 6, len(words))):
                if j >= len(words) or j >= len(pos_list):  # 修正：添加邊界檢查
                    break
                if re.match(r"^[「。！？,.!?、；;，」]$", words[j]) or pos_list[j] in BREAK_POS:
                    break
                if words[j] in NEGATIONS:
                    neg_count += 1
                    if debug:
                        print(f"  -> 目標詞 {words[i]} 後方找到否定詞: {words[j]} (index={j})")
            
            if debug:
                print(f"  -> 目標詞 {words[i]} 的 neg_count = {neg_count}")
            return neg_count

        # 處理副詞 + 模糊詞組合
        for i in range(len(words) - 1):
            if i + 1 < len(words) and words[i] in ADVERBS and words[i + 1] in FUZZY_WORDS:
                adv = words[i]
                word = words[i + 1]
                score = FUZZY_WORDS[word]["score"]
                direction = FUZZY_WORDS[word]["direction"]
                count_word += 1

                adv_weight = ADVERBS[adv]
                conf_pos = score if direction == "pos" else 0
                conf_neg = score if direction == "neg" else 0
                adv_pos_weight = adv_weight if direction == "pos" else 1
                adv_neg_weight = adv_weight if direction == "neg" else 1

                partial_score = (conf_pos ** adv_pos_weight) - (conf_neg ** adv_neg_weight)

                neg_count = check_negation(i + 1)
                if neg_count % 2 == 1:
                    partial_score *= -1

                if debug:
                    print(f"副詞+模糊詞組合: {adv}+{word}, partial_score={partial_score}")

                final_score += partial_score
                matched_indices.update({i, i + 1})

        # 處理單獨的模糊詞
        for i, word in enumerate(words):
            if i not in matched_indices and word in FUZZY_WORDS:
                score = FUZZY_WORDS[word]["score"]
                direction = FUZZY_WORDS[word]["direction"]
                count_word += 1

                conf_pos = score if direction == "pos" else 0
                conf_neg = score if direction == "neg" else 0
                partial_score = (conf_pos ** 1.0) - (conf_neg ** 1.0)

                neg_count = check_negation(i)
                if neg_count % 2 == 1:
                    partial_score *= -1

                if debug:
                    print(f"單詞: {word}, partial_score={partial_score}")

                final_score += partial_score
                matched_indices.add(i)

        # 計算平均分數
        if count_word != 0:
            final_score = final_score / count_word
        else:
            if debug:
                print("警告：未找到任何模糊詞")

        # 確定結果 - 修正：避免使用 np.nan
        if final_score > 0:
            result = "true"  # 真
        elif final_score < 0:
            result = "false"  # 假
        else:
            result = "unknown"  # 無法判斷

        if debug:
            print("=== Final Result ===")
            print("final_score:", final_score, " result:", result)
            print(f"處理了 {count_word} 個模糊詞")

        return {"final_score": final_score, "result": result, "word_count": count_word}

    except Exception as e:
        if debug:
            print(f"計算過程發生錯誤: {e}")
        return {"final_score": 0.0, "result": "unknown", "error": str(e)}



class ScoreDetail(BaseModel):
    evidence_quality: int = Field(ge=0, le=30, description="證據品質 0~30")
    logical_rigor: int = Field(ge=0, le=30, description="邏輯嚴謹性 0~30")
    robustness: int = Field(ge=0, le=20, description="論證韌性 0~20")
    social_impact: int = Field(ge=0, le=20, description="社會影響力 0~20")
    total: int = Field(ge=0, le=100, description="四項加總")


class Finding(BaseModel):
    point: str
    refs: List[str] = Field(default_factory=list, description="可附上引用的URL清單")


class JuryOutput(BaseModel):
    verdict: str = Field(description="簡短結論：如 '正方較有說服力' 或 '證據不足'")
    scores: ScoreDetail
    strengths: List[Finding] = Field(description="哪一方強在哪裡（2~5 條）")
    weaknesses: List[Finding] = Field(description="主要缺陷或風險（2~5 條）")
    flagged_fallacies: List[str] = Field(default_factory=list, description="主持人或評審辨識的邏輯謬誤")
    next_questions: List[str] = Field(default_factory=list, description="尚待澄清/查證的重點問題")

class JuryOutputfinal(BaseModel):
    verdict: str = Field(description="簡短結論：如 '正方較有說服力' 或 '證據不足'")
    scores: ScoreDetail
    strengths: List[Finding] = Field(description="哪一方強在哪裡（2~5 條）")
    weaknesses: List[Finding] = Field(description="主要缺陷或風險（2~5 條）")
    flagged_fallacies: List[str] = Field(default_factory=list, description="主持人或評審辨識的邏輯謬誤")
    next_questions: List[str] = Field(default_factory=list, description="尚待澄清/查證的重點問題")
    final_score: str = Field(description="最終分數，範圍從 -1 (拜速) 到 +1 (勝訴)")

def _ensure_and_flatten_fallacies(callback_context=None, **_):
    if callback_context is None:
        return None
    state = callback_context.state
    # 保底確保存在辯論訊息陣列，避免 KeyError
    msgs = state.get("debate_messages") or []
    state["debate_messages"] = msgs
    state["fallacy_list"] = flatten_fallacies(msgs)
    return None


jury_pretty_after = None

def _build_jury_after():
    def _after(agent_context=None, **_):
        if agent_context is None:
            return None
        st = agent_context.state
        out = st.get("jury_result")
        if out is None:
            return None
        try:
            if hasattr(out, "model_dump"):
                data = out.model_dump()
            else:
                data = out
            msg = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            msg = str(out)
        return Event(author="jury", actions=EventActions(message=msg))
    return _after

jury_pretty_after = _build_jury_after()

jury_agent_first = LlmAgent(
    name="jury2",
    model="gemini-2.5-flash",
    instruction=(
        "你是陪審團，請根據完整辯論紀錄與證據，進行客觀量化評分並給出裁決。\n\n"
        "【輸入】\n"
        "CURATION(JSON): {curation}\n"
        "ADVOCACY(JSON): (the current advocacy JSON in state['advocacy'], if any)\n"
        "SKEPTICISM(JSON): (the current skepticism JSON in state['skepticism'], if any)\n"
        "DEBATE(LOG): (the current debate messages stored in state['debate_messages'])\n"
        "SOCIAL_LOG(JSON): {social_log}\n\n"
        "【評分規則】\n"
        "- evidence_quality: 來源權威性/時效性/相關性（0~30）\n"
        "- logical_rigor: 是否自洽、是否有謬誤（0~30）\n"
        "- robustness: 面對反駁與極端質疑的韌性（0~20）\n"
        "- social_impact: 根據 SOCIAL_LOG 中的反應評估潛在影響與擾動（0~20）\n"
        "合計 total 0~100。\n\n"
        "【輸出】\n"
        "嚴格輸出 JSON，必須符合 JuryOutput schema；不要多餘文字。"
    ),
    output_schema=JuryOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="jury_result",
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
    before_agent_callback=_ensure_and_flatten_fallacies,
    after_agent_callback=jury_pretty_after,
)

text_agent = LlmAgent(
    name="text_processor",
    model="gemini-2.0-flash",
    instruction="""你是一個文本分數計算處理助手。你需要：

        1. 從當前 conversation 的 state 中取得 jury_result 的輸出結果
        2. 調用 calculate_fuzzy_score 函數來計算加權分數
        3. 將結果存儲到 state 中

        請按以下步驟操作：
        - 取得 state['jury_result'] 的內容
        - 將其作為 state_data 參數傳入 calculate_fuzzy_score 函數
        - 設定 debug=False 以減少輸出

        現在請調用 calculate_fuzzy_score 函數。""",
    tools=[calculate_fuzzy_score],
    output_key="weight_calculation_result",
)
text_check_schema_agent = LlmAgent(
    name="fact_check_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "你負責把 state['jury_result'] 和state['weight_calculation_result']轉為符合 FactCheckFFinalOutput schema 的 JSON，"
        "分析文章 news_text，使用 news_date 作為判斷基準。"
        "僅輸出最終 JSON（不要多餘文字）。"
    ),
    output_schema=JuryOutputfinal,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="JuryOutputfinal_json",
    generate_content_config=types.GenerateContentConfig(temperature=0.4),
)

jury_agent = SequentialAgent(
    name="jury",
    sub_agents=[jury_agent_first, text_agent,text_check_schema_agent],
)