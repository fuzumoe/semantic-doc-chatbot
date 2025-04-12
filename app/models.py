from pydantic import BaseModel


class ChatMessageSent(BaseModel):
    """Model for chat message sent by the user."""

    session_id: str
    user_input: str
    data_source: str
