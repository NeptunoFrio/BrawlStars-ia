import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .contracts import CONTRACT_VERSION

ALLOWED = {".onnx": "onnx", ".zip": "ppo"}
SAFE_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _paths():
    root = Path(os.getenv("BRAWLBOT_DATA_DIR", "./data")).resolve()
    mdir = root / "models"
    reg = root / "registry.json"
    return root, mdir, reg


def _load():
    root, mdir, reg = _paths()
    root.mkdir(parents=True, exist_ok=True)
    mdir.mkdir(parents=True, exist_ok=True)
    if not reg.exists():
        reg.write_text(
            json.dumps({"active_model": None, "last_error": None, "models": []}, indent=2)
        )
    return json.loads(reg.read_text())


def _save(data):
    root, _, reg = _paths()
    root.mkdir(parents=True, exist_ok=True)
    tmp = reg.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(reg)


def list_models():
    return _load()


def get_model(model_id: str):
    return next((m for m in _load()["models"] if m["id"] == model_id), None)


def add_model(filename: str, content: bytes, description: str = "", version: str = "1.0.0"):
    clean = SAFE_RE.sub("_", Path(filename or "model.onnx").name).strip("._")
    ext = Path(clean).suffix.lower()
    if ext not in ALLOWED:
        raise ValueError("Formato no permitido. Usa .onnx o .zip.")
    if not content or len(content) > 200 * 1024 * 1024:
        raise ValueError("Archivo vacío o mayor a 200 MB.")

    _, mdir, _ = _paths()
    mdir.mkdir(parents=True, exist_ok=True)
    model_id = uuid.uuid4().hex[:12]
    target = (mdir / f"{model_id}_{clean}").resolve()
    if mdir.resolve() not in target.parents:
        raise ValueError("Ruta inválida.")

    target.write_bytes(content)
    data = _load()
    item = {
        "id": model_id,
        "filename": clean,
        "path": str(target),
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "format": ext[1:],
        "brain_type": ALLOWED[ext],
        "version": version,
        "description": description,
        "contract_version": CONTRACT_VERSION,
        "validated": False,
        "validation_error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data["models"].append(item)
    _save(data)
    return item


def mark_validation(model_id: str, validated: bool, error: str | None = None):
    data = _load()
    for m in data["models"]:
        if m["id"] == model_id:
            m["validated"] = validated
            m["validation_error"] = error
    if error:
        data["last_error"] = {"model_id": model_id, "error": error}
    _save(data)


def set_active_model_id(model_id: str | None):
    data = _load()
    if model_id and not any(m["id"] == model_id for m in data["models"]):
        raise KeyError("Modelo no encontrado.")
    data["active_model"] = model_id
    _save(data)
    return data


def delete_model(model_id: str):
    data = _load()
    item = next((m for m in data["models"] if m["id"] == model_id), None)
    if not item:
        raise KeyError("Modelo no encontrado.")
    Path(item["path"]).unlink(missing_ok=True)
    data["models"] = [m for m in data["models"] if m["id"] != model_id]
    if data["active_model"] == model_id:
        data["active_model"] = None
    _save(data)
    return data


def register_trained_model(
    source_path: str | Path,
    *,
    brain_type: str = "ppo",
    description: str = "Modelo PPO entrenado en el simulador abstracto",
    version: str = "1.0.0",
    filename: str | None = None,
    activate: bool = False,
) -> dict:
    """
    Registra un modelo ya generado (por ejemplo desde train_ppo)
    dentro del Model Manager, reutilizando la misma lógica de add_model.
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"No se encontró el modelo: {source}")

    content = source.read_bytes()
    final_name = filename or source.name

    item = add_model(
        filename=final_name,
        content=content,
        description=description,
        version=version,
    )

    # Asegurar brain_type correcto (add_model lo infiere por extensión)
    if item["brain_type"] != brain_type:
        data = _load()
        for m in data["models"]:
            if m["id"] == item["id"]:
                m["brain_type"] = brain_type
        _save(data)
        item["brain_type"] = brain_type

    if activate:
        set_active_model_id(item["id"])

    return item
