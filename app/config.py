from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CampusStudy Estadísticas"
    database_url: str = "sqlite:///./data/estadisticas.db"
    seed_on_start: bool = True
    cors_origins: str = "*"
    usuarios_service_url: str = ""
    materias_service_url: str = ""
    tareas_service_url: str = ""
    grupos_service_url: str = ""
    http_timeout_seconds: float = 3.0
    http_reintentos: int = 2
    # Segundos que un reporte se sirve desde caché antes de volver a consultar a los demás servicios.
    cache_ttl_seconds: int = 60
    # Token de servicio a servicio. Si el Frontend envía Authorization, se reenvía ese en su lugar.
    servicio_token: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
