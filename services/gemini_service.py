"""Gemini resim üretme API'si ile iletişim."""
import io
import os

from PIL import Image

import config


class GeminiNotConfigured(Exception):
    pass


class GeminiGenerationError(Exception):
    pass


def _build_client(api_key: str | None = None):
    from google import genai  # local import: paket kurulu değilse app import edilebilsin

    key = (api_key or config.GEMINI_API_KEY or "").strip()
    if not key:
        raise GeminiNotConfigured(
            "Gemini API anahtarı tanımlı değil. Lütfen ayarlar panelinden girin "
            "veya .env dosyasına GEMINI_API_KEY ekleyin."
        )
    return genai.Client(api_key=key)


def generate_image(prompt: str, reference_image_path: str | None = None, api_key: str | None = None) -> Image.Image:
    from google.genai import types

    client = _build_client(api_key)

    contents = []
    if reference_image_path and os.path.exists(reference_image_path):
        contents.append(Image.open(reference_image_path))
    contents.append(prompt)

    try:
        response = client.models.generate_content(
            model=config.GEMINI_IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )
    except Exception as exc:  # ağ/anahtar/limit hataları
        raise GeminiGenerationError(f"Gemini isteği başarısız oldu: {exc}") from exc

    if not response.candidates:
        raise GeminiGenerationError(
            "Gemini herhangi bir yanıt üretmedi (istek güvenlik filtrelerine takılmış olabilir)."
        )

    candidate = response.candidates[0]
    if not candidate.content or not candidate.content.parts:
        finish_reason = getattr(candidate, "finish_reason", "bilinmiyor")
        raise GeminiGenerationError(f"Gemini görsel üretmedi (finish_reason={finish_reason}).")

    text_parts = []
    for part in candidate.content.parts:
        inline_data = getattr(part, "inline_data", None)
        if inline_data is not None and inline_data.data:
            return Image.open(io.BytesIO(inline_data.data))
        if getattr(part, "text", None):
            text_parts.append(part.text)

    message = " ".join(text_parts)[:400] or "bilinmeyen sebep"
    raise GeminiGenerationError(f"Gemini bir görsel döndürmedi. Model yanıtı: {message}")
