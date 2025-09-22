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
class WeightCalculationInput(BaseModel):
    llm_label: str = Field(description="fact_check_agent的分類標籤")
    slm_score: float = Field(description="bert_classifier_agent真新聞機率")
    jury_score: float = Field(description="Jury_agent的判斷分數-Jury_score")

class WeightCalculationOutput(BaseModel):
    llm_label: str = Field(description="LLM分類標籤")
    llm_score: float = Field(description="LLM標籤對應分數")
    slm_score: float = Field(description="SLM真新聞機率")
    jury_score: float = Field(description="Jury的判斷分數")
    final_score: float = Field(description="最終加權分數")

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
        jury_weight = 0.1
        
        # 嘗試解析傳入的 state 數據
        try:
            if state_data and state_data.strip():
                parsed_state = json.loads(state_data)
                llm_result = parsed_state.get("fact_check_result_json")
                slm_result = parsed_state.get("classification_json")
                # 修正：正確獲取 jury 結果
                jury_result = parsed_state.get("JuryOutputfinal_json")
                
                logger.info(f"解析的 state 數據鍵值: {list(parsed_state.keys())}")
                logger.info(f"Jury 結果: {jury_result}")
                
            else:
                logger.warning("未提供有效的 state_data")
                llm_result = None
                slm_result = None
                jury_result = None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析錯誤: {e}")
            llm_result = None
            slm_result = None
            jury_result = None
        
        # 解析結果 - 添加更嚴格的 None 檢查
        if llm_result is not None:
            if isinstance(llm_result, str):
                try:
                    llm_data = json.loads(llm_result)
                except json.JSONDecodeError:
                    logger.warning("LLM 結果 JSON 解析失敗，使用預設值")
                    llm_data = {"classification": "無法判斷"}
            elif isinstance(llm_result, dict):
                llm_data = llm_result
            else:
                logger.warning(f"LLM 結果格式異常: {type(llm_result)}")
                llm_data = {"classification": "無法判斷"}
        else:
            logger.warning("未找到 LLM 結果，使用預設值")
            llm_data = {"classification": "無法判斷"}
            
        if slm_result is not None:
            if isinstance(slm_result, str):
                try:
                    slm_data = json.loads(slm_result)
                except json.JSONDecodeError:
                    logger.warning("SLM 結果 JSON 解析失敗，使用預設值")
                    slm_data = {"Probability": 0.5}
            elif isinstance(slm_result, dict):
                slm_data = slm_result
            else:
                logger.warning(f"SLM 結果格式異常: {type(slm_result)}")
                slm_data = {"Probability": 0.5}
        else:
            logger.warning("未找到 SLM 結果，使用預設值")
            slm_data = {"Probability": 0.5}

        if jury_result is not None:
            if isinstance(jury_result, str):
                try:
                    jury_data = json.loads(jury_result)
                except json.JSONDecodeError:
                    logger.warning("Jury 結果 JSON 解析失敗，使用預設值")
                    jury_data = {"judge_score": "0.0"}
            elif isinstance(jury_result, dict):
                jury_data = jury_result
            else:
                logger.warning(f"Jury 結果格式異常: {type(jury_result)}")
                jury_data = {"judge_score": "0.0"}
        else:
            logger.warning("未找到 Jury 結果，使用預設值")
            jury_data = {"judge_score": "0.0"}
        
        # 轉換 LLM 標籤為分數 - 添加安全檢查
        llm_label = llm_data.get("classification", "無法判斷") if isinstance(llm_data, dict) else "無法判斷"
        llm_score = label_to_score.get(llm_label, 0.5)
        
        # 取得 SLM 分數 - 添加安全檢查
        if isinstance(slm_data, dict):
            slm_prob = slm_data.get("Probability", 0.5)
        else:
            slm_prob = 0.5
            
        try:
            slm_score = float(slm_prob)
        except (ValueError, TypeError):
            logger.warning(f"SLM 分數轉換失敗: {slm_prob}，使用預設值 0.5")
            slm_score = 0.5

        # 修正：正確取得 Jury 分數 - 添加安全檢查
        if isinstance(jury_data, dict):
            jury_score_raw = jury_data.get("judge_score", "0.0")
        else:
            jury_score_raw = "0.0"
            
        try:
            if isinstance(jury_score_raw, str):
                jury_score = float(jury_score_raw)
            else:
                jury_score = float(jury_score_raw)
        except (ValueError, TypeError):
            logger.warning(f"Jury 分數轉換失敗: {jury_score_raw}，使用預設值 0.0")
            jury_score = 0.0
        
        logger.info(f"提取的分數 - LLM: {llm_score}, SLM: {slm_score}, Jury: {jury_score}")
        
        # 計算最終加權分數：(標籤分數*LLM權重 + SLM分數*SLM權重) / (LLM權重 + SLM權重)
        base_score = (llm_score * llm_weight + slm_score * slm_weight) / (llm_weight + slm_weight)
        
        # 根據 jury_score 調整最終分數
        if jury_score > 0:
            final_score = base_score * (1 + jury_weight)
        elif jury_score < 0:
            final_score = base_score * (1 - jury_weight)
        else:
            final_score = base_score
        
        # 確保分數在 0-1 範圍內
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
            "llm_label": "錯誤",
            "llm_score": 0.0,
            "slm_score": 0.0,
            "jury_score": 0.0,
            "final_score": 0.0,
            "error": str(e)
        }
# -----------------------
# 初始化模型部分
# -----------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_name = "bert-base-chinese"

try:
    model_name_test = "bert-base-chinese"
    tokenizer_test = BertTokenizerFast.from_pretrained(r"D:\Agent-Judge-slm\judge\agents\classifier\bert_fake_news_model")
    model_test = BertForSequenceClassification.from_pretrained(r"D:\Agent-Judge-slm\judge\agents\classifier\bert_fake_news_model").to(device)
    model_test.eval()  # 設定為評估模式

    id2label = {0: "真", 1: "假"}
    
    logger.info("BERT 模型載入成功")
    
except Exception as e:
    logger.error(f"模型載入失敗: {e}")
    raise

# -----------------------
# 定義分類函數作為工具
# -----------------------
def classify_text(text: str) -> dict:
    """
    使用 BERT 模型分類文本真假
    
    Args:
        text: 要分類的文本
        
    Returns:
        包含分類結果的字典
    """
    logger.info(f"開始分類文本: {text[:50]}...")
    
    try:
        with torch.no_grad():
            encoding = tokenizer_test(
                        text,
                        padding="max_length",
                        truncation=True,
                        max_length=512,
                        return_tensors="pt"
                    ).to(device)

            # 丟進模型
            outputs = model_test(**encoding)

            # softmax 機率
            probs = torch.softmax(outputs.logits, dim=1).cpu().numpy()[0]

            # 模型預測標籤 (0=真新聞, 1=假新聞)
            pred_label = probs.argmax()

            # 只取 label=0 (真新聞) 的機率
            prob_label0 = probs[0].item()
            pred_label_text = id2label.get(pred_label, str(pred_label))


        result = {
            "label": pred_label_text,
            "scoProbabilityre": prob_label0,
            "input_text": text
        }
        
        logger.info(f"分類完成: {pred_label_text} (confidence: {prob_label0:.3f})")
        return result
        
    except Exception as e:
        logger.error(f"分類過程中發生錯誤: {e}")
        return {
            "label": "錯誤",
            "Probability": 0.0,
            "input_text": text,
            "error": str(e)
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
                    - JuryOutputfinal_json 中該包含 'judge_score' 欄位
                    - SLM 的最終輸出鍵值是 'classification_json'
                    - classification_json 中該包含 'Probability' 欄位
                    - 不要混淆不同的 state 資訊

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