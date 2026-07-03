"""Küçük yardımcı fonksiyonlar."""
import re


def sanitize_filename(name: str) -> str:
    """Dosya sistemi için güvenli, fakat Türkçe karakterleri koruyan bir isim üretir."""
    name = str(name or "").strip()
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip(". ")
    return name or "gorsel"
