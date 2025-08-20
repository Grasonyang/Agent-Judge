from src.base_agent import BaseAgent


class Skeptic(BaseAgent):
    """懷疑者代理類別

    角色任務：
        針對主張提出質疑，檢驗論點的完整性與可靠度。

    輸入資料格式：
        `claim` (`str`): 需要被質疑的主張內容。

    輸出資料格式：
        `str`: 懷疑者提出的關鍵質疑句。
    """

    def run(self, claim: str) -> str:
        """執行質疑流程

        參數:
            claim (str): 目標主張。

        回傳:
            str: 引導重新檢視主張的疑問句。
        """
        return f"我們有足夠證據支持『{claim}』嗎？"
