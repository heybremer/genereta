"""Excel satırlarını yüklenen görsel dosya adlarıyla eşleştirme ve prompt üretme."""
import os
import re


def normalize(value: str) -> str:
    value = str(value or "").strip().lower()
    value = value.replace("ı", "i")
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _stem(filename: str) -> str:
    return os.path.splitext(filename)[0]


def render_prompt(template: str, row: dict) -> str:
    """`{Sütun Adı}` şeklindeki yer tutucuları satır verisiyle değiştirir."""
    result = template
    for col, val in row.items():
        result = result.replace("{" + str(col) + "}", str(val))
    return result


def match_images_to_rows(rows: list, key_column: str, image_filenames: list):
    """Her excel satırını, dosya adı (uzantısız) eşleşen bir görsele bağlar.

    Döner: (eşleşme_listesi, eşleşmeyen_görsel_dosyaları)
    eşleşme_listesi elemanları: {"row": dict, "key_value": str, "image_filename": str|None}
    """
    image_lookup = {}
    for fname in image_filenames:
        key = normalize(_stem(fname))
        image_lookup.setdefault(key, fname)

    matched_image_names = set()
    results = []
    for row in rows:
        key_value = str(row.get(key_column, "")).strip()
        image_filename = image_lookup.get(normalize(key_value))
        if image_filename:
            matched_image_names.add(image_filename)
        results.append(
            {"row": row, "key_value": key_value, "image_filename": image_filename}
        )

    unmatched_images = [f for f in image_filenames if f not in matched_image_names]
    return results, unmatched_images
