# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SCREENER_SESSION_ID = os.environ.get("SCREENER_SESSION_ID", "")
    SCREENER_CSRF_TOKEN = os.environ.get("SCREENER_CSRF_TOKEN", "")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
    MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES", 50))
    TOP_N_FOR_NEWS = int(os.getenv("TOP_N_FOR_NEWS", 15))
    TOP_N_FINAL_REPORT = int(os.getenv("TOP_N_FINAL_REPORT", 10))
    CACHE_SCREENER = os.getenv("CACHE_SCREENER", "true").lower() == "true"
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

settings = Settings()
