from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: Path = Path("/app/data")
    database_url: str = "sqlite+aiosqlite:////app/data/plateblank.db"
    max_upload_size: int = 20 * 1024 * 1024  # 20 MB
    allowed_extensions: set[str] = {".jpg", ".jpeg", ".png", ".webp"}

    @property
    def originals_dir(self) -> Path:
        return self.data_dir / "originals"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "plateblank.db"

    model_config = {"env_prefix": "PLATEBLANK_"}


settings = Settings()
