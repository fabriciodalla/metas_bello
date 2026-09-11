from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR.parent / ".env")

# Sem fallback: um SECRET_KEY previsível compromete sessões, tokens de redefinição de senha e
# assinaturas CSRF — a aplicação deve recusar iniciar em vez de rodar com um valor conhecido.
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Origin do frontend (Vite dev server) — necessário porque o proxy do Vite preserva o header
# Origin do navegador mesmo reescrevendo o Host para o alvo interno (ver docker-compose.yml).
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=["http://localhost:5173"])

# Endurecimento de cookies/transporte: desligado por padrão em dev (DEBUG=True, acesso local por
# http://localhost:5173) e ligado por padrão em produção (DEBUG=False, atrás do túnel Cloudflare,
# sempre HTTPS) — DJANGO_SECURE_COOKIES permite forçar o valor nos dois sentidos se precisar.
SECURE_COOKIES = env.bool("DJANGO_SECURE_COOKIES", default=not DEBUG)
SESSION_COOKIE_SECURE = SECURE_COOKIES
CSRF_COOKIE_SECURE = SECURE_COOKIES
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
if SECURE_COOKIES:
    # Obrigatório junto de *_COOKIE_SECURE: sem isso, por trás de um proxy/túnel que termina TLS
    # antes da aplicação, o Django vê a requisição como HTTP simples e o cookie Secure nunca seria
    # definido — quebrando o login (ver nginx.conf / SECURE_PROXY_SSL_HEADER).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.accounts",
    "apps.hierarchy",
    "apps.catalog",
    "apps.cycles",
    "apps.allocations",
    "apps.audit",
    "apps.sales_history",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if not DEBUG:
    # Só entra fora de DEBUG: em dev, `runserver` já serve os estáticos sozinho (staticfiles app) e
    # ninguém roda collectstatic — WhiteNoise sem STATIC_ROOT populado só gera aviso à toa. Em
    # produção (gunicorn, sem runserver) é ele quem serve /static/ (Django Admin, DRF browsable
    # API) sem precisar de outro container/volume compartilhado com o nginx.
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


DATABASES = {"default": env.db("DATABASE_URL", default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')}

# Postgres externo do histórico de vendas (somente leitura, ver docs/architecture.md). Nenhum
# model/migração é atribuído a este alias — só cursor bruto no adaptador SalesHistoryProvider.
# Registrado só quando configurado; se vazio, nada tenta conectar.
if env("SALES_HISTORY_DATABASE_URL", default=""):
    DATABASES["sales_history"] = env.db("SALES_HISTORY_DATABASE_URL")

AUTH_USER_MODEL = "accounts.User"

# E-mail (link de definição/redefinição de senha). Sem SMTP configurado ainda: o backend padrão só
# imprime o e-mail no log do processo (`docker compose logs backend`). Configure
# DJANGO_EMAIL_BACKEND + as variáveis EMAIL_* quando houver um servidor de e-mail real.
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="naoresponda@bello.local")

# URL do frontend, usada para montar o link enviado por e-mail (ex.: /redefinir-senha/...).
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Serve CSS/JS do Django Admin (e da API navegável do DRF) direto pelo processo do gunicorn em
    # produção, sem depender de outro container/volume compartilhado com o nginx (Decisão M-02).
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
        "password_reset": "5/min",
    },
}

# Validade do link de "definir senha" (primeiro acesso e recuperação, via PasswordResetConfirmView)
# — padrão do Django é 3 dias; 24h já é suficiente para o fluxo por e-mail e reduz a janela de uso
# de um link vazado/interceptado.
PASSWORD_RESET_TIMEOUT = env.int("DJANGO_PASSWORD_RESET_TIMEOUT", default=86400)
