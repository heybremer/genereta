"""Excel / CSV dosyalarını okuma ve önizleme üretme."""
import os
import uuid

import pandas as pd

import config


def _read_dataframe(path: str, ext: str) -> pd.DataFrame:
    if ext == ".csv":
        try:
            return pd.read_csv(path, dtype=str, sep=None, engine="python")
        except Exception:
            return pd.read_csv(path, dtype=str)
    return pd.read_excel(path, dtype=str)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df.fillna("")


def save_and_parse_excel(file_storage) -> dict:
    filename = file_storage.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in config.ALLOWED_EXCEL_EXT:
        raise ValueError(
            "Desteklenmeyen dosya türü. Lütfen .xlsx, .xls ya da .csv yükleyin."
        )

    excel_id = uuid.uuid4().hex
    saved_path = os.path.join(config.TMP_DIR, f"{excel_id}{ext}")
    file_storage.save(saved_path)

    try:
        df = _clean(_read_dataframe(saved_path, ext))
    except Exception as exc:
        raise ValueError(f"Excel dosyası okunamadı: {exc}") from exc

    if df.empty or len(df.columns) == 0:
        raise ValueError("Excel dosyasında okunabilir veri bulunamadı.")

    preview = df.head(8).astype(str).to_dict(orient="records")

    return {
        "excel_id": excel_id,
        "original_filename": filename,
        "columns": list(df.columns),
        "row_count": int(len(df)),
        "preview": preview,
    }


def find_excel_path(excel_id: str):
    for name in os.listdir(config.TMP_DIR):
        stem, ext = os.path.splitext(name)
        if stem == excel_id and ext.lower() in config.ALLOWED_EXCEL_EXT:
            return os.path.join(config.TMP_DIR, name)
    return None


def load_dataframe(excel_path: str) -> pd.DataFrame:
    ext = os.path.splitext(excel_path)[1].lower()
    return _clean(_read_dataframe(excel_path, ext))
