import psycopg

from api.config import settings


def get_erp_connection() -> psycopg.Connection:
    if not settings.erp_db_host:
        raise ErpConfigError("ERP_DB_HOST nao configurado")

    conninfo = (
        f"host={settings.erp_db_host} "
        f"port={settings.erp_db_port} "
        f"dbname={settings.erp_db_name} "
        f"user={settings.erp_db_user} "
        f"password={settings.erp_db_password} "
        f"sslmode={settings.erp_db_sslmode} "
        f"options=-c\\ default_transaction_read_only=on"
    )
    return psycopg.connect(conninfo, autocommit=True)


class ErpConfigError(Exception):
    pass


class ErpQueryError(Exception):
    pass
