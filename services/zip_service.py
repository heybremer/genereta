"""Üretilen görselleri tek bir zip dosyası halinde paketleme."""
import io
import os
import zipfile


def zip_outputs(outputs_dir: str, arc_folder_name: str) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(outputs_dir)):
            fpath = os.path.join(outputs_dir, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, arcname=f"{arc_folder_name}/{fname}")
    buffer.seek(0)
    return buffer
