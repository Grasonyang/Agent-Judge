"""代理的抽象基底類別定義"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BaseAgent(ABC):
    """提供代理名稱與注意力預算欄位的基底類別"""

    name: str
    attention_budget: int

    @abstractmethod
    def run(self) -> None:
        """執行代理的主要流程，子類別須實作此方法"""
        raise NotImplementedError
