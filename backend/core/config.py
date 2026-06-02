"""Application configuration via pydantic-settings.

Reads from .env file, environment variables, and defaults.
All configuration flows through this single module — no hardcoding.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM Gateway configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    default_provider: str = "ollama"
    default_model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    api_key: str = ""
    router_model: str = "phi3:mini"
    planner_model: str = "qwen2.5:7b"
    allow_cloud: bool = False
    cloud_for_complex: bool = False
    timeout: int = 60


class OllamaConfig(BaseSettings):
    """Ollama provider configuration."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_")

    base_url: str = "http://localhost:11434"


class VoiceConfig(BaseSettings):
    """Voice system configuration."""

    model_config = SettingsConfigDict(env_prefix="VOICE_")

    enabled: bool = False
    stt_provider: str = "faster_whisper"
    tts_provider: str = "edge"
    wake_word_enabled: bool = False
    wake_word: str = "jarvis"


class SecurityConfig(BaseSettings):
    """Security and permissions configuration."""

    model_config = SettingsConfigDict(env_prefix="SECURITY_")

    confirm_dangerous_actions: bool = True
    auto_approve_safe: bool = True
    max_shell_timeout: int = 30


class Settings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_prefix="JARVIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    # General
    env: str = "development"
    data_dir: Path = Path("./data")
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite:///data/jarvis.db"

    # UI
    ui_host: str = "127.0.0.1"
    ui_port: int = 8400
    ui_cors_origins: str = "http://localhost:5173,http://localhost:8400,http://127.0.0.1:8400,app://jarvis"

    # Voice
    voice: VoiceConfig = VoiceConfig()
    voice_enabled: bool = False
    stt_model: str = "base"

    # Security
    security: SecurityConfig = SecurityConfig()

    # LLM
    llm: LLMConfig = LLMConfig()
    ollama: OllamaConfig = OllamaConfig()

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ui_cors_origins.split(",") if o.strip()]

    @property
    def data_path(self) -> Path:
        p = Path(self.data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


# Singleton
settings = Settings()
