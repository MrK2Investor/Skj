import os
from pathlib import Path
from pydantic import BaseModel

class Settings(BaseModel):
    broker_url: str = os.getenv("BROKER_URL", "ws://localhost:8001/ws")
    volume_dir: Path = Path(os.getenv("VOLUME_DIR", "haystack_node/volumes"))
    max_volume_size: int = int(os.getenv("MAX_VOLUME_SIZE", str(100 * 1024 * 1024)))
    gateway_url: str = os.getenv("GATEWAY_URL", "http://localhost:8000")
    admin_token: str = os.getenv("ADMIN_TOKEN", "secret-admin-token")

settings = Settings()
