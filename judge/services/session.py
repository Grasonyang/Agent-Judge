"""Session 服務模組。"""

from google.adk.sessions.in_memory_session_service import InMemorySessionService

# 建立唯一的 SessionService，供整個應用程式共用
session_service: InMemorySessionService = InMemorySessionService()