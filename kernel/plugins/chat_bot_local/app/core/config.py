from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_SERVER: str = "http://localhost:11434/"
    OLLAMA_TEMPERATURE: float = 0

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
