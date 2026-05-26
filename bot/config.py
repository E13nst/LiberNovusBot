# stdlib
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
