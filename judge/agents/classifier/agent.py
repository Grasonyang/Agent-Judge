# root_agent.py
from google.adk.agents import LlmAgent, SequentialAgent
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer
import logging
from transformers import BertForSequenceClassification, BertTokenizerFast
from google.genai import types
from pydantic import BaseModel, Field

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------
# 初始化模型部分
# -----------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_name = "bert-base-chinese"

try:
    model_name_test = "bert-base-chinese"
    tokenizer_test = BertTokenizerFast.from_pretrained(r"D:\下載\Agent-Judge-main-last\Agent-Judge-main\judge\agents\classifier\bert_fake_news_model")
    model_test = BertForSequenceClassification.from_pretrained(r"D:\下載\Agent-Judge-main-last\Agent-Judge-main\judge\agents\classifier\bert_fake_news_model").to(device)
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

class classificationOutput(BaseModel):
    Probability: str = Field(description="真新聞的機率")
    classification: str = Field(description="真假分類：正確 或 錯誤")

# -----------------------
# 使用 LlmAgent 來處理用戶輸入
# -----------------------
bert_classifier_model_agent = LlmAgent(
    name="bert_classifier",
    model="gemini-2.0-flash",  # 使用一個簡單的模型來處理輸入
    instruction="""你是一個文本真假分類助手。當用戶提供任何文本時，你需要：

            1. 提取用戶輸入的文本
            2. 調用 classify_text 函數來分析文本的真假
            3. 以友好的方式回報結果

            例如，如果用戶輸入「假」，你應該對「假」這個字進行分類。
            如果用戶輸入「這個新聞是真的嗎？」，你應該對整個句子進行分類。

            請一定要去調用 classify_text 函數去計算，並將結果以清晰的格式回報給用戶。""",
    tools=[classify_text],  # 將我們的分類函數註冊為工具
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="classification_result"
)


classification_schema_agent = LlmAgent(
    name="bert_classifier_validator",
    model="gemini-2.5-flash",
    instruction=(
        "你負責把 state['classification_result'] 轉為符合 classificationOutput schema 的 JSON，"
        "分析文章 news_text，使用 news_date 作為判斷基準。"
        "僅輸出最終 JSON（不要多餘文字）。"
    ),
    #input_schema=FactCheckInput,
    output_schema=classificationOutput,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="classification_json",
    generate_content_config=types.GenerateContentConfig(temperature=0.4),
)

# -------- Step 3: Sequential pipeline --------
classifier_agent = SequentialAgent(
    name="bert_classifier_agent",
    sub_agents=[bert_classifier_model_agent, classification_schema_agent],
)
