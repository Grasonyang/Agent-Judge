# Agent-Judge
Agent 模擬社會：假新聞深度辨識架構

## Agent 角色與核心邏輯
### 資料預處理 Agent（The Curator）
- 將非結構化新聞轉為結構化資料
- 文本分析：NER、情緒分析、主題標籤
- 多媒體處理：圖片/影片比對與連結來源追溯

### 正反方 Agent（The Advocate & The Skeptic）
- Advocate：提供佐證與解釋
- Skeptic：尋找矛盾並核查來源

### 陪審團 Agent（The Arbiter）
- 以證據可信度、邏輯一致性、傳播軌跡、情感強度等維度評分並仲裁

### 群眾 Agent（The Masses）
- 模擬不同社會群體的資訊傳播與情緒感染

### 謠言製造者 Agent（The Disrupter）
- 在關鍵時刻注入虛假資訊以測試系統韌性

## 系統運作流程
1. 使用者輸入新聞，Curator 產生結構化資料  
2. 新聞於 Masses 網路傳播並記錄情緒  
3. Advocate 與 Skeptic 進行辯論，Disrupter 視情況插入  
4. Arbiter 統合所有數據計算可信度分數  

## 最終輸出
- 總體可信度分數
- 主要爭議點
- 傳播力與情緒影響
- 佐證資料鏈

## 迴圈與 A2A 機制
- 每個 Agent 有限的注意力資源，避免無限迴圈
- Arbiter 結合辯論與傳播數據做出終止判斷

## 快速上手
1. 取得程式碼並建立虛擬環境：
   ```bash
   git clone https://github.com/your-account/Agent-Judge.git
   cd Agent-Judge
   python -m venv .venv
   source .venv/bin/activate
   ```
2. 安裝依賴（需先安裝 Google SDK）：
   ```bash
   pip install google-cloud-sdk
   ```
3. 執行測試：
   ```bash
   python -m pytest
   ```
