import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    def validate(self) -> None:
        if not self.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is missing. Set it in backend/.env")


settings = Settings()
settings.validate() 