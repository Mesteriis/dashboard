from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Store"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    # Storage
    storage_path: str = "./store/plugins"
    max_plugin_size_mb: int = 100
    allowed_extensions: tuple[str, ...] = (".zip", ".tar", ".gz")

    # GitHub
    github_token: str | None = None
    github_api_base: str = "https://api.github.com"

    # Security
    api_key: str | None = None  # Optional API key for authentication

    # CORS
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]


settings = Settings()
