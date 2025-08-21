from google.adk.agents import Agent

root_agent = Agent(
    name="weather_time_agent",
    model="gemini-2.5-flash",
    description=(
        "回答有關城市時間和天氣的問題。"
    ),
    instruction=(
        "無論使用者輸入何種語言，一律使用繁體中文回答。回答應簡潔一致，並提供有用的資訊。"
    )
)