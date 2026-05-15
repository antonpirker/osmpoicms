from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    osm_client_id: str
    osm_client_secret: str
    osm_redirect_uri: str = "http://localhost:8000/auth/callback"
    session_secret: str


settings = Settings()
