# 預期擴充
## 既有 Agent-Judge 加上分治
+ 構想：當輸入太長(1000 字以上)，從使用者 input 後(Curator 前)就進行 LLM 語意分段切割(每段 500 ~ 1500 字)，多開幾次庭，分別獨立處理。
最後也不用整合，將各結果串聯輸出即可。
+ 前後各加一個節點
## prompt 越疊越大，超過模型 token 配額
+ 測試輸入 2700 字文本，運行中途停止
+ 某子代理回傳 `errorCode: "MAX_TOKENS"`，顯示超過模型 token 配額
+ 當時 prompt 超大（promptTokenCount ≈ 22,966；totalTokenCount ≈ 23,989）
### 預期解法
1. 控制上下文大小
    + 針對會持續累加的欄位（如 state["debate_messages"]、social_noise.echo_chamber 等），每回合只保留「最近 N 則」或「摘要後」的文本（例如最後 4-6 交互，或硬上限 2–4k tokens）。已在啟動時初始化過，但要加「回合內剪枝」。
    + 在進入每個子代理前做「prompt 截斷/壓縮」：若偵測 promptTokenCount 將超過閾值（例如 16k），先做摘要，再交給模型。
2. 下修生成配額、改小模型或分批
    + 為長文分析的子代理（如 fallacy_detector / noise_aggregator）降低 max_output_tokens，避免回傳超長；或改用更經濟的模型做中繼摘要。
    + 把多段分析拆批次（串行）而非硬併行，至少對最大的兩個角色序列化，先削 prompt 體積再進下一個。
3. 在 synthesizer 之前做「終局摘要」
    + 加一道「壓縮器」代理，把整個 state 壓到固定上限（例如 ≤6k tokens），再讓 synthesizer_agent 產 JSON，避免末段再爆。
    + 若 ADK 支援 streaming/分塊，啟用以減輕單輪 token 壓力。

## google search 不要綁 gemini？
+ 所有`tools=[GoogleSearchTool()]`？
+ 如：`root_agent\agents\curator\agent.py`_`curator_tool_agent`
+ 避免抓錯或抓太多導致 token 爆掉
+ 直接用 google search 或其他 tool 抓
+ 或是下更嚴格的 prompt，如：不要抓錯誤網頁、只回傳精簡後文字
