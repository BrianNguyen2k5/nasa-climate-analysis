import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class AIConfig:
    gemini_api_key: str | None
    groq_api_key: str | None
    gemini_primary_model: str
    gemini_backup_model: str
    groq_primary_model: str
    groq_backup_model: str
    groq_code_model: str


def load_ai_config() -> AIConfig:
    load_dotenv()
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    groq_api_key = os.getenv("GROQ_API_KEY")

    return AIConfig(
        gemini_api_key=gemini_api_key,
        groq_api_key=groq_api_key,
        gemini_primary_model=os.getenv(
            "GEMINI_PRIMARY_MODEL",
            "gemini-2.5-flash",
        ),
        gemini_backup_model=os.getenv(
            "GEMINI_BACKUP_MODEL",
            "gemini-2.0-flash",
        ),
        groq_primary_model=os.getenv(
            "GROQ_PRIMARY_MODEL",
            "llama-3.3-70b-versatile",
        ),
        groq_backup_model=os.getenv(
            "GROQ_BACKUP_MODEL",
            "llama-3.1-8b-instant",
        ),
        groq_code_model=os.getenv(
            "GROQ_CODE_MODEL",
            "qwen/qwen3.6-27b",
        ),
    )

