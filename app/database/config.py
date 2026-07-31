import os
from dotenv import load_dotenv

load_dotenv()


class DatabaseConfig:
    URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/guardrail")
    ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"
    POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))


class HITLConfig:
    """Human-in-the-loop workflow configuration."""

    EXPIRY_HOURS: float = float(os.getenv("HITL_EXPIRY_HOURS", "24"))
