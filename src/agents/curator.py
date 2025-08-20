from src.base_agent import BaseAgent


class Curator(BaseAgent):
    """策展者代理類別

    角色任務：
        接收多筆文字資料並進行去重與條列整理，提供清晰摘要。

    輸入資料格式：
        `materials` (`list[str]`): 原始資訊集合。

    輸出資料格式：
        `list[str]`: 清理後的資訊摘要清單。
    """

    def run(self, materials: list[str]) -> list[str]:
        """執行策展流程

        參數:
            materials (list[str]): 待整理的文字資訊。

        回傳:
            list[str]: 去重且去除前後空白的資訊摘要。
        """
        unique_items = []
        for item in materials:
            cleaned = item.strip()
            if cleaned and cleaned not in unique_items:
                unique_items.append(cleaned)
        return unique_items
