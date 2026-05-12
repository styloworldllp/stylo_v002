# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/config.py
#
# Central settings object — reads from .env.control (or environment variables)
# at startup using pydantic-settings.  All other modules import the `settings`
# singleton at the bottom rather than reading os.environ directly.
#
# Key setting groups:
#   database_url   — PostgreSQL async URL (asyncpg driver for SQLAlchemy)
#   redis_url      — Redis used as Celery broker + result backend
#   secret_key     — JWT signing key for admin session tokens
#   smtp_*         — SMTP credentials for license-expiry email alerts
#   slack_webhook  — Optional Slack webhook for alert notifications
#   traefik_*      — SSH details for the Traefik load-balancer host so the
#                    control center can push updated sites.yml via SFTP
# ─────────────────────────────────────────────────────────────────────────────
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://stylo:stylo@postgres:5432/stylo_control"

    # Redis (for Celery tasks)
    redis_url: str = "redis://redis:6379/0"

    # Auth — control center admin JWT secret
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8 hours

    # Alerts
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_from_email: str = "alerts@styloworld.io"
    slack_webhook_url: str = ""

    # Traefik load balancer
    traefik_server_host: str = ""
    traefik_ssh_user: str = "root"
    traefik_ssh_key_path: str = "/root/.ssh/id_rsa"
    traefik_config_path: str = "/etc/traefik/dynamic/sites.yml"

    class Config:
        env_file = ".env.control"


settings = Settings()
