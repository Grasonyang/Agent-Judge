"""Judge 套件初始化。

此模組原本在載入時即匯入 `root_agent`，但這會造成部分模組
在匯入過程中因循環依賴而失敗。為了讓工具模組可以獨立使用，
這裡改為延遲載入 `root_agent`：需要使用時再從 `judge.agent`
匯入。
"""

root_agent = None  # 將在需要時由呼叫端自行匯入

__all__ = ["root_agent"]

