# weight_calculator_agent.py
from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types
from pydantic import BaseModel, Field
import json
import logging

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
    final_score: float = Field(description="最終加權分數")
    weights: dict = Field(description="使用的權重")

# -----------------------
# 權重計算函數
# -----------------------
def calculate_weighted_score(state_data: str = "") -> dict:
    """
    從 state 中取得其他 agent 的結果並計算權重分數
    
    Args:
        state_data: 包含 state 信息的字符串（通常由 LlmAgent 傳入）
        
    Returns:
        包含權重計算結果的字典
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
        
        # 嘗試解析傳入的 state 數據
        try:
            if state_data and state_data.strip():
                parsed_state = json.loads(state_data)
                llm_result = parsed_state.get("fact_check_result_json")
                slm_result = parsed_state.get("classification_json")
            else:
                llm_result = None
                slm_result = None
        except json.JSONDecodeError:
            llm_result = None
            slm_result = None
        
        # 如果沒有從參數取得，使用預設範例（你需要替換為實際的 state key）
        """if llm_result is None:
            # 這裡你需要替換為實際從 state 取得的方式
            # 例如：llm_result = agent.get_state("classification_json")
            llm_result = agent.get_state("fact_check_result_json")
        
        if slm_result is None:
            # 這裡你需要替換為實際從 state 取得的方式  
            # 例如：slm_result = agent.get_state("bert_result")
            slm_result = agent.get_state("classification_json")"""
        
        # 解析結果
        if isinstance(llm_result, str):
            llm_data = json.loads(llm_result)
        else:
            llm_data = llm_result
            
        if isinstance(slm_result, str):
            slm_data = json.loads(slm_result)
        else:
            slm_data = slm_result
        
        # 轉換 LLM 標籤為分數
        llm_label = llm_data.get("classification", "完全錯誤")
        llm_score = label_to_score.get(llm_label, 0.0)
        
        # 取得 SLM 分數
        slm_score = float(slm_data.get("score", 0.0))
        
        # 計算最終加權分數：(標籤分數*LLM權重 + SLM分數*SLM權重) / (LLM權重 + SLM權重)
        final_score = (llm_score * llm_weight + slm_score * slm_weight) / (llm_weight + slm_weight)
        
        result = {
            "llm_label": llm_label,
            "llm_score": llm_score,
            "slm_score": slm_score,
            "final_score": round(final_score, 4),
            "weights": {"llm": llm_weight, "slm": slm_weight}
        }
        
        logger.info(f"權重計算完成: 最終分數 {final_score:.4f}")
        return result
        
    except Exception as e:
        logger.error(f"權重計算過程中發生錯誤: {e}")
        return {
            "llm_label": "錯誤",
            "llm_score": 0.0,
            "slm_score": 0.0,
            "final_score": 0.0,
            "weights": {"llm": 0.6, "slm": 0.4},
            "error": str(e)
        }

# -----------------------
# 使用 LlmAgent 來處理權重計算
# -----------------------
weight_processor_agent = LlmAgent(
    name="weight_processor",
    model="gemini-2.0-flash",
    instruction="""你是一個權重計算處理助手。你需要：

1. 從當前 conversation 的 state 中取得其他 agent 的結果
2. 將 LLM agent 的分類結果和 SLM agent 的分數結果傳給 calculate_weighted_score 函數
3. 調用該函數來計算加權分數

SLM的結果為 state['classification_json']
LLM的結果為 state['fact_check_result_json']
請按以下格式調用函數，將 state 中的相關數據作為參數傳入：
- 如果能直接訪問 state，請將 LLM 和 SLM 的結果組織成 JSON 字符串傳入
- 函數會自動處理標籤轉分數和權重計算

現在請調用 calculate_weighted_score 函數。""",
    tools=[calculate_weighted_score],
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