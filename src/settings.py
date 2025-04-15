"""
Параметры окружения, взятые из .env
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    TESTERS_IDS: str
    LOG_FILE: str
    LOG_LEVEL: str
    WORDS_FILE: str
    STATE_SAVE_DIR: str
    CHATS_STATS_DIR: str
    GLOBAL_STATS_FILE: str

    GAME_TIME: int
    EXCLUSIVE_TIME: int
    FAULT_SIZE: int  # Кол-во пропусков за который дается штраф

    # --- Статистика ---
    CHAT_STATS_SIZE: int
    GLOBAL_STATS_SIZE: int

    # --- Параметры админки ---
    CHAT_PAGE_SIZE: int

    # ChatGPT
    GPT_INJECTION: bool
    OPEN_API_KEY: str
    GPT_MODEL: str
    PROMPT_FILE: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
