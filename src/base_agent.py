"""代理的抽象基底類別定義"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class BaseAgent(ABC):
    """提供代理名稱與注意力預算欄位的基底類別"""

    name: str
    attention_budget: int

    @abstractmethod
    def run(self, data: Any | None = None) -> Any:
        """執行代理的主要流程

        參數:
            data (Any | None):
                執行所需的輸入資料，型別與結構由子類別自行定義。

        回傳:
            Any: 依子類別設計回傳相應的結果資料。
        """
        raise NotImplementedError
