from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_BYTES = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql://nara:nara@localhost:5432/nara"

    jwt_secret: str = "development-only-secret-do-not-ship-this"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 30

    # When this holds a built frontend, the API serves it too and everything is one origin.
    static_dir: str = "static"
    cors_origins: str = "http://localhost:5173"
    app_base_url: str = "http://localhost:5173"
    # "lax" suits a same-origin deployment (or the Vite dev proxy); use "none" for a cross-site API.
    cookie_samesite: str = "lax"

    trial_days: int = 14
    trial_seat_limit: int = 10
    invite_expiry_days: int = 7
    # How long a failed payment keeps working before the account suspends.
    past_due_grace_days: int = 7

    # Payroll is usually paid in quarter hours; set to 0 to export exact times instead.
    payroll_rounding_minutes: int = 15

    # Online brute-force protection. Per-IP limits belong at the proxy, not in the app process.
    max_failed_logins: int = 8
    lockout_minutes: int = 15

    # A laptop locating itself by Wi-Fi is often hundreds of metres out, so weak fixes can't start a shift.
    max_gps_accuracy_m: int = 100
    min_zone_radius_m: int = 50
    max_zone_radius_m: int = 300
    default_zone_radius_m: int = 150
    open_shift_flag_hours: int = 12

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cookies_secure(self) -> bool:
        return self.environment != "development"

    @model_validator(mode="after")
    def _reject_a_weak_production_secret(self) -> "Settings":
        if self.environment != "development" and len(self.jwt_secret) < MIN_SECRET_BYTES:
            raise ValueError(f"JWT_SECRET must be at least {MIN_SECRET_BYTES} characters outside development")
        return self


settings = Settings()
