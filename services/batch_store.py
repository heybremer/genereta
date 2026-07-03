"""Bellek içi (ve diske yansıtılan) toplu iş (batch) deposu."""
import json
import os
import threading
import uuid
from datetime import datetime, timezone

import config

_LOCK = threading.RLock()
_BATCHES: dict = {}


def create_batch(excel_filename, key_column, prompt_template, folder_name, items, order):
    batch_id = uuid.uuid4().hex[:12]
    batch_dir = os.path.join(config.BATCHES_DIR, batch_id)
    uploads_dir = os.path.join(batch_dir, "uploads")
    outputs_dir = os.path.join(batch_dir, "outputs")
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)

    batch = {
        "id": batch_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "excel_filename": excel_filename,
        "key_column": key_column,
        "prompt_template": prompt_template,
        "folder_name": folder_name or "gorseller",
        "dir": batch_dir,
        "uploads_dir": uploads_dir,
        "outputs_dir": outputs_dir,
        "items": items,
        "order": order,
    }
    with _LOCK:
        _BATCHES[batch_id] = batch
    persist(batch)
    return batch


def get_batch(batch_id: str):
    with _LOCK:
        batch = _BATCHES.get(batch_id)
    if batch:
        return batch
    return _load_from_disk(batch_id)


def update_item(batch_id: str, item_id: str, **fields):
    with _LOCK:
        batch = get_batch(batch_id)
        if not batch:
            raise KeyError("Batch bulunamadı")
        item = batch["items"].get(item_id)
        if item is None:
            raise KeyError("Öğe bulunamadı")
        item.update(fields)
        persist(batch)
        return item


def persist(batch: dict):
    path = os.path.join(batch["dir"], "state.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)


def _load_from_disk(batch_id: str):
    batch_dir = os.path.join(config.BATCHES_DIR, batch_id)
    state_path = os.path.join(batch_dir, "state.json")
    if not os.path.exists(state_path):
        return None
    with open(state_path, "r", encoding="utf-8") as f:
        batch = json.load(f)
    with _LOCK:
        _BATCHES[batch_id] = batch
    return batch
