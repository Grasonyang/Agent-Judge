from src.base_agent import BaseAgent


class Arbiter(BaseAgent):
    """仲裁者代理類別

    角色任務：
        接收多方意見並計算多數決結果，輸出最終裁決。

    輸入資料格式：
        `opinions` (`list[str]`): 各參與者的意見列表。

    輸出資料格式：
        `str`: 經過多數決後的裁決結論。
    """

    def run(self, opinions: list[str]) -> str:
        """執行仲裁流程

        參數:
            opinions (list[str]): 各方提出的意見。

        回傳:
            str: 多數決產生的裁決內容。
        """
        if not opinions:
            return "無可裁決意見"

        # 以出現頻率最高的意見作為裁決
        decision = max(set(opinions), key=opinions.count)
        return f"裁決結果：{decision}"
