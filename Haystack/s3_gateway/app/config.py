from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    broker_url: str = "ws://localhost:8001/ws"
    haystack_url: str = "http://localhost:8003"
    admin_token: str = "secret-admin-token"
    image_worker_url: str = "http://localhost:8002"


    initial_credits: int = 100_000
    upload_credit_per_kib: int = 1
    download_credit_per_kib: int = 0

settings = Settings()
