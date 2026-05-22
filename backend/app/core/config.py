from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "数据资产管理平台"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./data_assets.db"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DASHSCOPE_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
