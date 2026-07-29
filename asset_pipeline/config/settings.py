import os
from dotenv import load_dotenv

load_dotenv()

LEONARDO_API_KEY = os.environ.get("LEONARDO_API_KEY", "")
HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY", "")