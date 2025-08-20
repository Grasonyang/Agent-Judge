from google.adk import Agent


class Disrupter(Agent):
    """破壞者代理類別

    角色任務：
        針對既定的假設或流程提出反向觀點，促進創新與反思。

    輸入資料格式：
        `status_quo` (`str`): 目前被視為理所當然的現狀描述。

    輸出資料格式：
        `str`: 對現狀提出挑戰的疑問或觀點。
    """

    def run(self, status_quo: str) -> str:
        """執行破壞流程

        參數:
            status_quo (str): 需要被質疑或挑戰的現狀。

        回傳:
            str: 促使重新思考的挑戰語句。
        """
        return f"如果我們不再遵循『{status_quo}』，會產生什麼新可能？"
