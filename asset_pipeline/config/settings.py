import os
from dotenv import load_dotenv

load_dotenv()

LEONARDO_API_KEY = os.environ.get("LEONARDO_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",")]