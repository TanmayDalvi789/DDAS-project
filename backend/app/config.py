import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "DDAS Backend"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server
    api_port: int = 8001
    api_host: str = "0.0.0.0"
    api_workers: int = 4
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "postgresql://ddas_user:ddas_password@localhost:5432/ddas_db"

    # JWT
    jwt_secret_key: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_port: int = 6379

    # S3 / Storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "ddas-storage"
    s3_use_ssl: bool = False

    # FAISS
    faiss_index_path: str = "./faiss_indices"
    faiss_index_name: str = "ddas_main"
    faiss_dimension: int = 384

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/backend.log"

    # Feature Toggles
    enable_semantic_search: bool = True
    enable_fuzzy_matching: bool = True
    enable_exact_matching: bool = True

    # Detection Thresholds
    fuzzy_threshold: float = 0.8
    semantic_threshold: float = 0.7
    fusion_warn_threshold: float = 0.5
    fusion_block_threshold: float = 0.85

    # Rate Limiting
    rate_limit_per_second: int = 100
    rate_limit_storage_url: str = "redis://localhost:6379/1"

    # Embedding Model
    embedding_model_name: str = "all-MiniLM-L6-v2"

    # Maintenance
    maintenance_mode: bool = False

    # Security
    cors_origins: list = ["http://localhost:3000", "http://localhost:8080"]
    allowed_hosts: list = ["localhost", "127.0.0.1", "testserver"]

    # Organization / User
    enable_signup: bool = False

    # Storage Config
    storage_type: str = "local"
    local_storage_path: str = "./storage"

    # Redis Worker Config
    redis_host: str = "localhost"
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Worker Configuration
    worker_name: str = "ddas-worker-1"
    worker_timeout: int = 3600
    worker_result_ttl: int = 500
    worker_failure_ttl: int = 86400
    worker_max_jobs: Optional[str] = None  # Can be empty string from env

    # Detection
    exact_match_enabled: bool = True
    max_sample_size: int = 1000

    # Development
    reload: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields

    @property
    def CORS_ORIGINS(self):
        """Return CORS origins (uppercase for compatibility)."""
        return self.cors_origins

    @property
    def ALLOWED_HOSTS(self):
        """Return allowed hosts (uppercase for compatibility)."""
        return self.allowed_hosts

    @property
    def ENVIRONMENT(self):
        """Return environment (uppercase for compatibility)."""
        return self.environment

    @property
    def DEBUG(self):
        """Return debug flag (uppercase for compatibility)."""
        return self.debug

    @property
    def HOST(self):
        """Return host (uppercase for compatibility)."""
        return self.host

    @property
    def PORT(self):
        """Return port (uppercase for compatibility)."""
        return self.port

    # Backwards-compatible Redis aliases (some modules expect uppercase names)
    @property
    def REDIS_HOST(self):
        return self.redis_host

    @property
    def REDIS_PORT(self):
        return self.redis_port

    @property
    def REDIS_DB(self):
        return self.redis_db

    @property
    def REDIS_PASSWORD(self):
        return self.redis_password


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
