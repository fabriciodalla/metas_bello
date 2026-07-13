from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://metas:metas@db:5432/metas_bello"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 480
    algorithm: str = "HS256"

    erp_db_host: str = ""
    erp_db_port: int = 5432
    erp_db_name: str = ""
    erp_db_schema: str = "stage"
    erp_db_user: str = ""
    erp_db_password: str = ""
    erp_db_sslmode: str = "prefer"
    erp_db_sales_history_relation: str = "cr8be_vendas_bello_2"

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
