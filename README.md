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

## 專案結構要點（對齊 Architecture）
- `judge/agents/moderator/`：辯論層（Core Debate Arena）
  - `agent.py`：決策/執行/停迴圈（Moderator orchestrator + Loop）
  - `tools.py`：主持人工具與事件紀錄
  - `advocate/agent.py`、`skeptic/agent.py`、`devil/agent.py`（正反與 Devil 置於主持人之下）
- `judge/agents/knowledge/`：資料與脈絡層
  - `curator/agent.py`、`historian/agent.py`
- `judge/agents/adjudication/`：裁決與整合層
  - `evidence/agent.py`、`jury/agent.py`、`synthesizer/agent.py`
- `judge/agents/social/`：社會擴散與噪音回饋層
  - `agent.py`：社會擴散統整，產出 `social_log`
  - `noise/agent.py`：噪音模擬與聚合，產出 `state['social_noise']`
  - `echo/agent.py`：Echo Chamber 子代理
  - `influencer/agent.py`：Influencer 子代理（支援多個）
  - `disrupter/agent.py`：Disrupter 子代理
- `judge/tools/`：統一工具
  - `session_service.py`（服務集中於 tools）
  - `debate_log.py`、`fallacies.py`、`file_io.py`、`evidence.py`

相容性：常用路徑（如 `judge.agents.moderator.agent`、`judge.agents.moderator.advocate.agent`）與舊位置提供薄包裝 re-export，避免現有呼叫點破壞。

## Session/State
本專案全面採用 Google ADK 的 Session/State/Memory：
- `judge/tools/session_service.py` 建立全域 `InMemorySessionService`（服務集中於 tools）。
- 事件透過 `google.adk.events.Event` 寫入，並由 `judge.tools.append_event` 同步更新 `session.state` 與 `debate_messages`。
- `judge/tools/debate_log.py` 僅作為從 Session 匯總回合（Turn）與導出 JSON 的輔助，不再作為單獨來源。

## 測試與 CI/CD
```bash
pytest
```
目前 CI/CD 狀態：已配置 GitHub Actions（`ci.yml`, `cd.yml`）進行持續整合與部署。
