from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    data_dir: Path = Path("../data")
    cors_origins: str = "*"
    max_file_size: int = 524_288_000  # 500 MB
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_default_model: str = "base"

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
