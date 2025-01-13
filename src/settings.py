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

    GAME_TIME: int
    EXCLUSIVE_TIME: int

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
