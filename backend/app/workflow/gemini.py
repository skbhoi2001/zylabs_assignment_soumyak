"""Shared Gemini client factory with retry logic for 429 rate limits."""
import time
import json
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MODEL = "gemini-2.5-flash"
MAX_RETRIES = 3


def get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def generate(prompt: str, system: Optional[str] = None) -> str:
    """Call Gemini with automatic retry on 429."""
    client = get_client()
    config = types.GenerateContentConfig(system_instruction=system) if system else None

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=config,
            )
            return response.text
        except ClientError as exc:
            if exc.status_code == 429 and attempt < MAX_RETRIES - 1:
                wait = 30 * (attempt + 1)
                logger.warning(f"Gemini 429 rate limit — retrying in {wait}s (attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
            else:
                raise


def strip_fences(raw: str) -> str:
    """Remove markdown code fences that models sometimes add despite instructions."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def chat_with_history(system: str, history: list, user_message: str) -> str:
    """Send a chat message with prior history and a system instruction."""
    client = get_client()

    gemini_history = []
    for msg in history:
        role = "model" if msg.role == "assistant" else "user"
        gemini_history.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))

    # Gemini requires history to start with a user turn
    while gemini_history and gemini_history[0].role == "model":
        gemini_history.pop(0)

    for attempt in range(MAX_RETRIES):
        try:
            chat = client.chats.create(
                model=MODEL,
                config=types.GenerateContentConfig(system_instruction=system),
                history=gemini_history,
            )
            response = chat.send_message(user_message)
            return response.text
        except ClientError as exc:
            if exc.status_code == 429 and attempt < MAX_RETRIES - 1:
                wait = 30 * (attempt + 1)
                logger.warning(f"Gemini chat 429 — retrying in {wait}s")
                time.sleep(wait)
            else:
                raise
