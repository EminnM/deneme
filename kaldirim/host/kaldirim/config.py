from __future__ import annotations

import os
from pathlib import Path

import yaml


def load(path: str | None = None) -> dict:
    p = Path(path or os.environ.get("KALDIRIM_CONFIG", "config.yaml"))
    if not p.exists():
        raise SystemExit(f"config not found: {p} (copy config.example.yaml to config.yaml)")
    with p.open() as f:
        cfg = yaml.safe_load(f)
    cfg["data_dir"] = str(Path(cfg.get("data_dir", "./data")).resolve())
    for sub in ("clips", "exports", "site"):
        Path(cfg["data_dir"], sub).mkdir(parents=True, exist_ok=True)
    return cfg
