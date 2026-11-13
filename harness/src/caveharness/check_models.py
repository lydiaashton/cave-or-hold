"""Live model-list check (handoff section 3): is every study ID served?

    uv run python -m caveharness.check_models

Reads keys from the environment, harness/.env or the repository root's .env
(in that order of precedence). Prints model IDs and whatever
metadata each provider returns about them -- never a key. A provider whose key
is not set is reported as skipped, not failed.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

import httpx
from dotenv import load_dotenv

from caveharness.config import ENV_FILES, RUNS_DIR

STUDY = {
    "adaption": ["qwen3.5-397b", "glm-5.2", "deepseek-v4-flash"],
    "anthropic": ["claude-opus-5", "claude-fable-5"],
    "openai": ["gpt-6-astra"],
    "google": ["gemini-4-argon"],
}


def _adaption(key: str) -> list[dict]:
    r = httpx.get("https://api.prod.adaptionlabs.ai/api/v1/models",
                  params={"type": "hosted"},
                  headers={"Authorization": f"Bearer {key}"}, timeout=60)
    r.raise_for_status()
    body = r.json()
    return body.get("data", body) if isinstance(body, dict) else body


def _anthropic(key: str) -> list[dict]:
    r = httpx.get("https://api.anthropic.com/v1/models", params={"limit": 1000},
                  headers={"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=60)
    r.raise_for_status()
    return r.json().get("data", [])


def _openai(key: str) -> list[dict]:
    r = httpx.get("https://api.openai.com/v1/models",
                  headers={"Authorization": f"Bearer {key}"}, timeout=60)
    r.raise_for_status()
    return r.json().get("data", [])


def _google(key: str) -> list[dict]:
    # Key in a header, never the URL: an error message prints the URL.
    r = httpx.get("https://generativelanguage.googleapis.com/v1beta/models",
                  params={"pageSize": 1000}, headers={"x-goog-api-key": key}, timeout=60)
    r.raise_for_status()
    return [{**m, "id": m.get("name", "").removeprefix("models/")}
            for m in r.json().get("models", [])]


PROVIDERS = {
    "adaption": ("ADAPTION_API_KEY", _adaption),
    "anthropic": ("ANTHROPIC_API_KEY", _anthropic),
    "openai": ("OPENAI_API_KEY", _openai),
    "google": ("GOOGLE_API_KEY", _google),
}


def main() -> int:
    for env_file in ENV_FILES:   # harness/.env first; it wins over the root .env
        load_dotenv(env_file)
    report = {"checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "providers": {}}
    for name, (var, fn) in PROVIDERS.items():
        key = os.environ.get(var)
        if not key:
            print(f"{name:10} skipped: {var} not set")
            report["providers"][name] = {"status": "skipped", "reason": f"{var} not set"}
            continue
        try:
            models = fn(key)
        except Exception as ex:
            msg = str(ex).replace(key, "***")   # belt and braces: never print a key
            print(f"{name:10} ERROR: {type(ex).__name__}: {msg[:200]}")
            report["providers"][name] = {"status": "error", "error": msg[:500]}
            continue
        ids = {str(m.get("id")): m for m in models if isinstance(m, dict)}
        found = {}
        for want in STUDY[name]:
            m = ids.get(want)
            found[want] = m
            print(f"{name:10} {want:20} {'FOUND' if m else 'NOT LISTED'}")
            if m:
                extra = {k: v for k, v in m.items() if k not in ("id", "object")}
                print(f"{'':10} {'':20} {json.dumps(extra)[:400]}")
        report["providers"][name] = {"status": "ok", "n_models_listed": len(ids),
                                     "study_models": found}
    out = RUNS_DIR / "model_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
