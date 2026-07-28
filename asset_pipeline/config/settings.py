import os
from dotenv import load_dotenv

load_dotenv()

LEONARDO_API_KEY = os.environ.get("LEONARDO_API_KEY", "")