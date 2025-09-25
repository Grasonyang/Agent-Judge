# weight_calculator_agent.py
from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from pydantic import BaseModel, Field
import json
import logging
from transformers import BertForSequenceClassification, BertTokenizerFast
import torch
import torch.nn as nn
import torch.nn.functional as F

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------
# 定義輸出格式
# -----------------------


class WeightCalculationOutput(BaseModel):
    llm_label: str = Field(description="LLM分類標籤")
    llm_score: float = Field(description="LLM標籤對應分數")
    slm_score: float = Field(description="SLM真新聞機率")
    jury_score: float = Field(description="Jury的判斷分數")
    final_score: float = Field(description="最終加權分數")
def calculate_weighted_score(state_data: str = "") -> dict:
    """
    從 state 中取得其他 agent 的結果並計算權重分數
    （移除所有預設值，抓不到資料就直接拋錯）
    """
    logger.info("開始權重計算...")

    try:
        # 標籤轉分數映射
        label_to_score = {
            "完全錯誤": 0.0,
            "部分錯誤": 0.25,
            "無法判斷": 0.5,
            "部分正確": 0.75,
            "完全正確": 1.0
        }

        # 權重設定
        llm_weight = 0.6
        slm_weight = 0.4
        jury_weight = 0.1

        # 嘗試解析傳入的 state 數據
        if not state_data or not state_data.strip():
            raise ValueError("未提供有效的 state_data")

        parsed_state = json.loads(state_data)

        # 嘗試取出結果
        llm_result = (
            parsed_state.get("fact_check_result_json")
            or parsed_state.get("LLM_output")
        )
        slm_result = (
            parsed_state.get("classification_json")
            or parsed_state.get("SLM_output")
        )
        jury_result = (
            parsed_state.get("JuryOutputfinal_json")
            or parsed_state.get("Jury_output")
        )

        if llm_result is None:
            raise ValueError("未找到 LLM 結果")
        if slm_result is None:
            raise ValueError("未找到 SLM 結果")
        if jury_result is None:
            raise ValueError("未找到 Jury 結果")

        # 解析 LLM
        if isinstance(llm_result, str):
            llm_data = json.loads(llm_result)
        elif isinstance(llm_result, dict):
            llm_data = llm_result
        else:
            raise TypeError(f"LLM 結果格式異常: {type(llm_result)}")

        llm_label = llm_data["classification"]
        llm_score = label_to_score[llm_label]

        # 解析 SLM
        if isinstance(slm_result, str):
            slm_data = json.loads(slm_result)
        elif isinstance(slm_result, dict):
            slm_data = slm_result
        else:
            raise TypeError(f"SLM 結果格式異常: {type(slm_result)}")

        slm_score = float(slm_data["Probability"])

        # 解析 Jury
        if isinstance(jury_result, str):
            jury_data = json.loads(jury_result)
        elif isinstance(jury_result, dict):
            jury_data = jury_result
        else:
            raise TypeError(f"Jury 結果格式異常: {type(jury_result)}")

        jury_score = float(jury_data["judge_score"])

        logger.info(f"提取的分數 - LLM: {llm_score}, SLM: {slm_score}, Jury: {jury_score}")

        # 計算最終分數
        base_score = (llm_score * llm_weight + slm_score * slm_weight) / (llm_weight + slm_weight)

        if jury_score > 0:
            final_score = base_score * (1 + jury_weight)
        elif jury_score < 0:
            final_score = base_score * (1 - jury_weight)
        else:
            final_score = base_score

        final_score = max(0.0, min(1.0, final_score))

        result = {
            "llm_label": llm_label,
            "llm_score": llm_score,
            "slm_score": slm_score,
            "jury_score": jury_score,
            "final_score": round(final_score, 4),
        }

        logger.info(f"權重計算完成: 最終分數 {final_score:.4f}")
        return result

    except Exception as e:
        logger.error(f"權重計算過程中發生錯誤: {e}")
        return {
            "error": str(e),
            "llm_label": None,
            "llm_score": None,
            "slm_score": None,
            "jury_score": None,
            "final_score": None,
        }



# -----------------------
# 使用 LlmAgent 來處理權重計算
# -----------------------
weight_processor_agent = LlmAgent(
    name="weight_processor",
    model="gemini-2.5-flash",
    instruction="""你是一個權重計算處理助手。你需要：
            從當前 conversation 的 state 中取得：
                    - SLM的結果為 state['classification_json'] (注意：是 classification_json，不是其他名稱)
                    - LLM的結果為 state['fact_check_result_json']  
                    - Jury的結果為 state['JuryOutputfinal_json'] (注意：是 JuryOutputfinal_json，不是其他名稱)

                    執行步驟：
                    1. 檢查並列出 state 中所有可用的鍵值
                    2. 提取上述三個結果的數據
                    3. 將這些數據組織成 JSON 格式傳給 calculate_weighted_score 函數
                    4. 如果某個數據缺失、或者轉檔出問題，請再重新處理格式，並密切注意抓取到的state 是否有數值你漏掉
                    5. 最多重試 3 次以確保獲取正確數據

                    請特別注意：
                    - Jury 的最終輸出鍵值是 'JuryOutputfinal_json'
                    - JuryOutputfinal_json 中該包含 'judge_score' 欄位，且應該是介於-1 ~ 1 之間
                    - SLM 的最終輸出鍵值是 'classification_json'
                    - classification_json 中該包含 'Probability' 欄位
                    - LLM 的最終輸出鍵值是 'fact_check_result_json'
                    - fact_check_result_json 中該包含 'classification' 欄位
                    - 不要混淆不同的 state 資訊
                    - 且一定要呼叫工具來做權重計算


        現在請調用 calculate_weighted_score 函數。""",
    tools=[calculate_weighted_score],
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
    output_key="weight_calculation_result"
)

# Schema 格式化 agent
weight_schema_agent = LlmAgent(
    name="weight_schema_validator",
    model="gemini-2.5-flash",
    instruction=(
        "你負責把 state['weight_calculation_result'] 轉為符合 WeightCalculationOutput schema 的 JSON。"
        "確保所有數值格式正確，分數保留 4 位小數。"
        "僅輸出最終 JSON（不要多餘文字）。"
    ),
    output_schema=WeightCalculationOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="weight_calculation_json",
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)

# -----------------------
# Sequential pipeline
# -----------------------
weight_agent = SequentialAgent(
    name="weight_calculator_agent",
    sub_agents=[weight_processor_agent, weight_schema_agent],
)