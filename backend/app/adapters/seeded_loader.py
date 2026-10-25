"""Data loader for static seeded demonstration datasets.

Reads JSON data files from app/data/ without making external calls or database queries.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_seeded_routes() -> List[Dict[str, Any]]:
    path = DATA_DIR / "routes.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_seeded_services() -> List[Dict[str, Any]]:
    path = DATA_DIR / "services.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_seeded_incidents() -> List[Dict[str, Any]]:
    path = DATA_DIR / "incidents.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
