from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://products:products@localhost:5432/products"
    )
    keycloak_issuer: str = "http://localhost:8081/realms/observabilidade"
    keycloak_jwks_url: str = (
        "http://localhost:8081/realms/observabilidade/"
        "protocol/openid-connect/certs"
    )
    keycloak_client_id: str = "products-api"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    seed_target_count: int = 2_000_000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

