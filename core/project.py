"""Save/load PV-Calc Pro project payloads as JSON."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
PROJECT_VERSION = 1


def _resolve_path(filename: str | Path) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(filename)
    if path.suffix.lower() != ".json":
        path = path.with_suffix(".json")
    if not path.is_absolute():
        path = OUTPUT_DIR / path.name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_project(filename: str | Path, payload: dict[str, Any]) -> Path:
    if not isinstance(payload, dict):
        raise ValueError("Проект должен сохраняться как словарь payload.")
    path = _resolve_path(filename)
    document = {
        "app": "PV-Calc Pro",
        "version": PROJECT_VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "payload": payload,
    }
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_project(filename: str | Path) -> dict[str, Any]:
    path = _resolve_path(filename)
    if not path.exists():
        raise FileNotFoundError(f"Файл проекта не найден: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("Файл проекта поврежден: корневой объект не является словарем.")
    if int(document.get("version", 0)) > PROJECT_VERSION:
        raise ValueError("Файл проекта создан более новой версией приложения.")
    payload = document.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Файл проекта поврежден: отсутствует словарь payload.")
    return payload
