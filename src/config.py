"""設定檔讀取範例"""
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# 透過 os.getenv 取得設定值
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")

# 使用範例：在其他模組中可以這樣引用
# from src.config import GEMINI_API_KEY
