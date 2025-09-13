<p align="center">
  <img src=".images/logo.png" alt="專案 Logo" width="200" />
</p>

# Agent-Judge

本專案為多代理辯論系統，目標在於對假新聞進行可觀察、可審計與可復現的分析，透過多角色協作產出結構化報告。

## 安裝
建議於 Python 3.12 以上的虛擬環境中安裝依賴：

```bash
python -m venv .venv
source .venv/bin/activate  # 啟用虛擬環境
pip install -r requirements.txt  # 安裝相依套件
```

### 主要相依套件版本

| 套件 | 版本 |
| --- | --- |
| google-adk | 1.14.0 |
| google-generativeai | 0.8.5 |
| pandas | 2.3.2 |
| pydantic | 2.11.9 |
| python-dotenv | 1.1.1 |
| pytest | 8.4.1 |
| rouge-score | 0.1.2 |
| tabulate | 0.9.0 |

## 執行
```bash
adk run root_agent
```

## 系統架構
![系統架構](.images/architecture.png)
Curator → Historian → Moderator 的流程自資料整理、歷史脈絡建構到辯論主持，逐步完成查核與分析。

## 測試與 CI/CD
```bash
pytest
```
目前 CI/CD 狀態：已配置 GitHub Actions（`ci.yml`, `cd.yml`）進行持續整合與部署。
