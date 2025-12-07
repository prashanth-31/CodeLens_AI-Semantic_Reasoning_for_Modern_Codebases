# config.py
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

DEFAULT_REPO_PATH = Path.cwd()
DOCS_DIR_NAME = "ai_docs"
LOCAL_MODEL_ID = os.getenv("LOCAL_MODEL_ID", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
MAX_CODE_CHARS = 4000
