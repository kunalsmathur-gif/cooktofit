"""Conversation core placeholder. Replaced by the coach agent in the conversation-core slice."""

from uuid import UUID

PLACEHOLDER = "Got it! Meal logging and recipes are coming soon."


async def respond(user_id: UUID, text: str | None) -> list[str]:
    return [PLACEHOLDER]
