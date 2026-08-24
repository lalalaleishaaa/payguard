import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "payguard.db")
    MAX_RETRY_ATTEMPTS = 2
    HIGH_VALUE_THRESHOLD = 5000
    LLM_MODEL = "anthropic/claude-sonnet-4"
    LLM_TIMEOUT = 10
    LLM_MAX_RETRIES = 3