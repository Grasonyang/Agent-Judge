from src.base_agent import BaseAgent


class Advocate(BaseAgent):
    """倡議者代理類別

    角色任務：
        針對特定提案生成正面論述，說服受眾接受該提案。

    輸入資料格式：
        `proposal` (`str`): 提案內容描述。

    輸出資料格式：
        `str`: 支持該提案的倡議陳述。
    """

    def run(self, proposal: str) -> str:
        """執行倡議流程

        參數:
            proposal (str): 需要倡議的提案內容。

        回傳:
            str: 結合正面論點後的倡議文字。
        """
        return f"我們應該推動{proposal}，它將帶來顯著的正面影響。"
