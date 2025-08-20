from src.base_agent import BaseAgent


class Masses(BaseAgent):
    """群眾代理類別

    角色任務：
        模擬多數群體對議題的回應，產生具代表性的集體觀點。

    輸入資料格式：
        `question` (`str`): 要詢問群眾的問題。
        `size` (`int`, 選用): 要模擬的群眾數量，預設為 3。

    輸出資料格式：
        `list[str]`: 群眾針對問題的各自回應。
    """

    def run(self, question: str, size: int = 3) -> list[str]:
        """執行群眾模擬

        參數:
            question (str): 需要回應的議題內容。
            size (int): 產生回應的模擬人數。

        回傳:
            list[str]: 模擬群眾的回應清單。
        """
        return [f"群眾{i + 1}：對『{question}』的看法" for i in range(size)]
