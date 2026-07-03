"""Uygulama genelinde kullanılan yapılandırma ve sabitler."""
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TMP_DIR = os.path.join(DATA_DIR, "tmp")
BATCHES_DIR = os.path.join(DATA_DIR, "batches")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image").strip()

ALLOWED_EXCEL_EXT = {".xlsx", ".xls", ".csv"}
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

# Excel + görsel yüklemelerine izin verilen toplam istek boyutu
MAX_CONTENT_LENGTH = 300 * 1024 * 1024  # 300 MB

for _dir in (DATA_DIR, TMP_DIR, BATCHES_DIR):
    os.makedirs(_dir, exist_ok=True)
