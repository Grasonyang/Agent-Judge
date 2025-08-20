"""Runner 設定範例

此範例示範如何建立即時保留對話上下文與長期記憶的 Runner，
並透過事件回呼監控工具調用與模型回覆。
"""

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.events.event import Event
from google.adk.plugins.base_plugin import BasePlugin
from google.genai.types import Content, Part


class EchoAgent(Agent):
    """回聲代理，只回傳使用者輸入文字"""

    def run(self, text: str) -> str:
        """回傳相同內容，示範用"""
        return f"回應：{text}"


class MonitorPlugin(BasePlugin):
    """簡易事件監聽插件，用於後續監控或 Guardrail 擴充"""

    async def on_event_callback(self, *, invocation_context, event: Event):
        """監聽工具調用與模型回覆"""
        # 檢查是否有工具被呼叫
        for fn in event.get_function_calls():
            print(f"工具呼叫：{fn.name}")

        # 監控模型回覆（非使用者事件）
        if event.author != "user":
            print(f"模型回覆：{event.content}")

        return None


# 建立 Session 與 Memory 服務
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()


# 建立 Runner，確保對話上下文與記憶保留
runner = Runner(
    app_name="agent-judge-demo",
    agent=EchoAgent(name="echo", model="gemini-1.5-flash"),
    session_service=session_service,
    memory_service=memory_service,
    plugins=[MonitorPlugin()],
)


async def demo() -> None:
    """示範如何使用 Runner 進行一次對話"""

    # 準備使用者訊息
    message = Content(role="user", parts=[Part.from_text("你好")])

    # 執行對話流程並處理事件
    async for event in runner.run_async(
        user_id="demo-user", session_id="demo-session", new_message=message
    ):
        # 此處可進一步處理事件，例如顯示或儲存
        pass

