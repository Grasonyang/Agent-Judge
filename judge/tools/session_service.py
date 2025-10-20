"""Global SessionService singleton within tools namespace."""

from google.adk.sessions.in_memory_session_service import InMemorySessionService

session_service: InMemorySessionService = InMemorySessionService()

