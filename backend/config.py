import os
from dotenv import load_dotenv

load_dotenv(override=True)  # .env wins over system environment variables


class Settings:
    # Gemini: embeddings only
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # Groq (OpenAI-compatible API): answer generation
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    llm_model: str = os.getenv("LLM_MODEL", "")

    def validate(self) -> None:
        missing = [
            name
            for name, value in {
                "GEMINI_API_KEY": self.gemini_api_key,
                "LLM_API_KEY": self.llm_api_key,
                "LLM_MODEL": self.llm_model,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing in backend/.env: {', '.join(missing)}")


settings = Settings()
settings.validate()  # fail fast at startup