"""Excel listesi + referans görsellere göre Gemini ile toplu görsel üreten uygulama."""
import glob
import os
import shutil
import traceback
import uuid

from flask import Flask, jsonify, render_template, request, send_file, send_from_directory, abort

import config
from services import batch_store, excel_service, gemini_service, matching, zip_service
from utils import sanitize_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

# Çalışma zamanında girilen API anahtarı (yalnızca bellekte tutulur, diske yazılmaz)
RUNTIME_SETTINGS = {"api_key": ""}


def _active_api_key() -> str:
    return RUNTIME_SETTINGS["api_key"] or config.GEMINI_API_KEY


def _public_item(batch: dict, item: dict) -> dict:
    reference_url = None
    if item.get("original_filename"):
        reference_url = f"/media/{batch['id']}/uploads/{item['original_filename']}"

    generated_url = None
    if item.get("generated_filename"):
        cache_bust = uuid.uuid4().hex[:6]
        generated_url = f"/media/{batch['id']}/outputs/{item['generated_filename']}?v={cache_bust}"

    return {
        "id": item["id"],
        "key_value": item["key_value"],
        "prompt": item["prompt"],
        "status": item["status"],
        "has_reference": bool(item.get("original_filename")),
        "reference_url": reference_url,
        "generated_url": generated_url,
        "error": item.get("error"),
    }


def _batch_payload(batch: dict) -> dict:
    order = batch.get("order") or list(batch["items"].keys())
    return {
        "batch_id": batch["id"],
        "folder_name": batch["folder_name"],
        "items": [_public_item(batch, batch["items"][i]) for i in order if i in batch["items"]],
    }


@app.route("/")
def index():
    return render_template("index.html", has_env_key=bool(config.GEMINI_API_KEY))


@app.route("/api/settings", methods=["GET", "POST"])
def settings_route():
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        RUNTIME_SETTINGS["api_key"] = (data.get("api_key") or "").strip()
        return jsonify({"ok": True, "configured": bool(_active_api_key())})
    return jsonify({"configured": bool(_active_api_key()), "has_env_key": bool(config.GEMINI_API_KEY)})


@app.route("/api/excel/upload", methods=["POST"])
def upload_excel():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "Excel dosyası bulunamadı."}), 400
    try:
        result = excel_service.save_and_parse_excel(file)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": f"Beklenmeyen hata: {exc}"}), 500
    return jsonify(result)


@app.route("/api/images/upload", methods=["POST"])
def upload_images():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "Görsel dosyası bulunamadı."}), 400

    images_id = uuid.uuid4().hex
    images_dir = os.path.join(config.TMP_DIR, f"images_{images_id}")
    os.makedirs(images_dir, exist_ok=True)

    saved = []
    skipped = []
    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in config.ALLOWED_IMAGE_EXT:
            skipped.append(f.filename)
            continue
        dest = os.path.join(images_dir, os.path.basename(f.filename))
        f.save(dest)
        saved.append(os.path.basename(f.filename))

    if not saved:
        return jsonify({"error": "Desteklenen bir görsel dosyası bulunamadı (png, jpg, jpeg, webp, bmp, gif)."}), 400

    return jsonify({"images_id": images_id, "filenames": saved, "skipped": skipped})


@app.route("/api/batch/create", methods=["POST"])
def create_batch():
    data = request.get_json(force=True, silent=True) or {}
    excel_id = (data.get("excel_id") or "").strip()
    images_id = (data.get("images_id") or "").strip()
    key_column = data.get("key_column") or ""
    prompt_template = (data.get("prompt_template") or "").strip()
    folder_name = sanitize_filename(data.get("folder_name") or "gorseller")

    if not (excel_id and images_id and key_column and prompt_template):
        return jsonify({"error": "Eksik bilgi: excel, görseller, eşleştirme sütunu ve prompt gereklidir."}), 400

    excel_path = excel_service.find_excel_path(excel_id)
    images_dir = os.path.join(config.TMP_DIR, f"images_{images_id}")
    if not excel_path or not os.path.isdir(images_dir):
        return jsonify({"error": "Yüklenen dosyalar bulunamadı, lütfen Excel ve görselleri tekrar yükleyin."}), 400

    try:
        df = excel_service.load_dataframe(excel_path)
    except Exception as exc:
        return jsonify({"error": f"Excel okunamadı: {exc}"}), 400

    if key_column not in df.columns:
        return jsonify({"error": "Seçilen eşleştirme sütunu excelde bulunamadı."}), 400

    rows = df.to_dict(orient="records")
    image_filenames = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]

    matches, unmatched_images = matching.match_images_to_rows(rows, key_column, image_filenames)

    items = {}
    order = []
    for m in matches:
        item_id = uuid.uuid4().hex[:10]
        prompt = matching.render_prompt(prompt_template, m["row"])
        items[item_id] = {
            "id": item_id,
            "key_value": m["key_value"],
            "row": m["row"],
            "prompt": prompt,
            "original_filename": m["image_filename"],
            "status": "matched" if m["image_filename"] else "no_image",
            "generated_filename": None,
            "error": None,
        }
        order.append(item_id)

    batch = batch_store.create_batch(
        excel_filename=os.path.basename(excel_path),
        key_column=key_column,
        prompt_template=prompt_template,
        folder_name=folder_name,
        items=items,
        order=order,
    )

    for item in items.values():
        if item["original_filename"]:
            src = os.path.join(images_dir, item["original_filename"])
            dst = os.path.join(batch["uploads_dir"], item["original_filename"])
            if os.path.exists(src):
                shutil.copy2(src, dst)

    payload = _batch_payload(batch)
    payload["unmatched_images"] = unmatched_images
    return jsonify(payload)


@app.route("/api/batch/<batch_id>", methods=["GET"])
def get_batch_route(batch_id):
    batch = batch_store.get_batch(batch_id)
    if not batch:
        return jsonify({"error": "Batch bulunamadı."}), 404
    return jsonify(_batch_payload(batch))


@app.route("/api/batch/<batch_id>/generate/<item_id>", methods=["POST"])
def generate_item(batch_id, item_id):
    batch = batch_store.get_batch(batch_id)
    if not batch:
        return jsonify({"error": "Batch bulunamadı."}), 404
    item = batch["items"].get(item_id)
    if not item:
        return jsonify({"error": "Öğe bulunamadı."}), 404

    reference_path = None
    if item.get("original_filename"):
        reference_path = os.path.join(batch["uploads_dir"], item["original_filename"])

    batch_store.update_item(batch_id, item_id, status="generating", error=None)

    try:
        image = gemini_service.generate_image(
            prompt=item["prompt"],
            reference_image_path=reference_path,
            api_key=_active_api_key(),
        )
    except gemini_service.GeminiNotConfigured as exc:
        item = batch_store.update_item(batch_id, item_id, status="error", error=str(exc))
        return jsonify({"error": str(exc), "item": _public_item(batch, item)}), 400
    except Exception as exc:
        traceback.print_exc()
        item = batch_store.update_item(batch_id, item_id, status="error", error=str(exc))
        return jsonify({"error": str(exc), "item": _public_item(batch, item)}), 502

    base_name = sanitize_filename(item["key_value"] or item_id)
    out_filename = f"{base_name}.png"
    out_path = os.path.join(batch["outputs_dir"], out_filename)
    try:
        image.save(out_path, "PNG")
    except OSError:
        image.convert("RGB").save(out_path, "PNG")

    item = batch_store.update_item(
        batch_id, item_id, status="done", generated_filename=out_filename, error=None
    )
    return jsonify({"item": _public_item(batch, item)})


@app.route("/media/<batch_id>/<kind>/<path:filename>")
def media(batch_id, kind, filename):
    if kind not in ("uploads", "outputs"):
        abort(404)
    batch = batch_store.get_batch(batch_id)
    if not batch:
        abort(404)
    directory = batch["uploads_dir"] if kind == "uploads" else batch["outputs_dir"]
    return send_from_directory(directory, filename)


@app.route("/api/batch/<batch_id>/download", methods=["GET"])
def download_batch(batch_id):
    batch = batch_store.get_batch(batch_id)
    if not batch:
        return jsonify({"error": "Batch bulunamadı."}), 404
    if not os.listdir(batch["outputs_dir"]):
        return jsonify({"error": "Henüz üretilmiş görsel yok."}), 400
    buffer = zip_service.zip_outputs(batch["outputs_dir"], batch["folder_name"])
    zip_name = f"{batch['folder_name']}.zip"
    return send_file(buffer, mimetype="application/zip", as_attachment=True, download_name=zip_name)


@app.errorhandler(413)
def too_large(_exc):
    return jsonify({"error": "Yüklenen dosyalar çok büyük."}), 413


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
