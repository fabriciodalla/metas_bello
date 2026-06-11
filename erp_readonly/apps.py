from django.apps import AppConfig


class ErpReadonlyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erp_readonly"
    verbose_name = "ERP read-only"
