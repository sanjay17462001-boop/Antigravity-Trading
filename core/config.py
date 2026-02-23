"""
Antigravity Trading — Configuration System
Loads YAML config and provides type-safe access via Pydantic models.
Supports environment variable overrides for secrets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
STORAGE_DIR = PROJECT_ROOT / "storage"
CANDLES_DIR = STORAGE_DIR / "candles"
LOGS_DIR = STORAGE_DIR / "logs"
DB_PATH = STORAGE_DIR / "trades.db"


# ---------------------------------------------------------------------------
# Pydantic config models
# ---------------------------------------------------------------------------

class DhanConfig(BaseModel):
    """Dhan API credentials — historical data source."""
    client_id: str = ""
    access_token: str = ""

    def resolve(self) -> "DhanConfig":
        return DhanConfig(
            client_id=os.getenv("DHAN_CLIENT_ID", self.client_id),
            access_token=os.getenv("DHAN_ACCESS_TOKEN", self.access_token),
        )


class BigulConfig(BaseModel):
    """Bigul / XTS API credentials — primary feed + execution."""
    api_key: str = ""
    api_secret: str = ""
    totp_secret: str = ""
    source: str = "WebAPI"
    market_url: str = "https://mtrade.arhamshare.com/apimarketdata"
    interactive_url: str = "https://mtrade.arhamshare.com/interactive"

    def resolve(self) -> "BigulConfig":
        return BigulConfig(
            api_key=os.getenv("BIGUL_API_KEY", self.api_key),
            api_secret=os.getenv("BIGUL_API_SECRET", self.api_secret),
            totp_secret=os.getenv("BIGUL_TOTP_SECRET", self.totp_secret),
            source=self.source,
            market_url=self.market_url,
            interactive_url=self.interactive_url,
        )


class KotakNeoConfig(BaseModel):
    """Kotak Neo API credentials — hot standby feed + execution."""
    consumer_key: str = ""
    consumer_secret: str = ""
    totp_secret: str = ""
    mobile_number: str = ""
    password: str = ""

    def resolve(self) -> "KotakNeoConfig":
        return KotakNeoConfig(
            consumer_key=os.getenv("KOTAK_CONSUMER_KEY", self.consumer_key),
            consumer_secret=os.getenv("KOTAK_CONSUMER_SECRET", self.consumer_secret),
            totp_secret=os.getenv("KOTAK_TOTP_SECRET", self.totp_secret),
            mobile_number=os.getenv("KOTAK_MOBILE", self.mobile_number),
            password=os.getenv("KOTAK_PASSWORD", self.password),
        )


class BrokersConfig(BaseModel):
    dhan: DhanConfig = Field(default_factory=DhanConfig)
    bigul: BigulConfig = Field(default_factory=BigulConfig)
    kotak_neo: KotakNeoConfig = Field(default_factory=KotakNeoConfig)


class RiskConfig(BaseModel):
    """Risk management parameters."""
    max_loss_per_day: float = 50000.0        # ₹ max loss per day
    max_loss_per_strategy: float = 20000.0   # ₹ max loss per strategy
    max_position_value: float = 500000.0     # ₹ max single position value
    max_open_positions: int = 10
    circuit_breaker_drawdown_pct: float = 5.0  # % of capital
    auto_square_off_nse: str = "15:15"       # HH:MM IST
    auto_square_off_mcx: str = "23:25"       # HH:MM IST


class DataConfig(BaseModel):
    """Data storage and fetch settings."""
    candles_dir: str = str(CANDLES_DIR)
    db_path: str = str(DB_PATH)
    default_interval: str = "5m"
    history_years: int = 5
    cache_enabled: bool = True


class LoggingConfig(BaseModel):
    level: str = "INFO"
    log_dir: str = str(LOGS_DIR)
    max_file_size_mb: int = 50
    backup_count: int = 10


class Settings(BaseModel):
    """Root settings object."""
    brokers: BrokersConfig = Field(default_factory=BrokersConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    initial_capital: float = 1_000_000.0     # ₹ starting capital

    def resolve_secrets(self) -> "Settings":
        """Resolve environment variable overrides for all broker secrets."""
        return Settings(
            brokers=BrokersConfig(
                dhan=self.brokers.dhan.resolve(),
                bigul=self.brokers.bigul.resolve(),
                kotak_neo=self.brokers.kotak_neo.resolve(),
            ),
            risk=self.risk,
            data=self.data,
            logging=self.logging,
            initial_capital=self.initial_capital,
        )


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_settings: Optional[Settings] = None


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """Load settings from YAML file, with env-var overrides for secrets."""
    global _settings

    if config_path is None:
        config_path = CONFIG_DIR / "settings.yaml"

    if config_path.exists():
        with open(config_path, "r") as f:
            raw = yaml.safe_load(f) or {}
        settings = Settings(**raw)
    else:
        settings = Settings()

    _settings = settings.resolve_secrets()
    return _settings


def get_settings() -> Settings:
    """Get the current settings (loads defaults if not yet loaded)."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
