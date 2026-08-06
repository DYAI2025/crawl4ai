#!/usr/bin/env python3
"""Check whether Crawl4AI and its browser tooling are available.

This script performs read-only checks and never installs packages or browsers.
"""
from __future__ import annotations

import argparse
import importlib
import json
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

TARGET_VERSION = "0.9.2"
MIN_PYTHON = (3, 10)


def _module_version(module: Any) -> str | None:
    for attr in ("__version__", "VERSION", "version"):
        value = getattr(module, attr, None)
        if isinstance(value, str):
            return value
    try:
        version_module = importlib.import_module("crawl4ai.__version__")
        value = getattr(version_module, "__version__", None)
        return value if isinstance(value, str) else None
    except Exception:
        return None


def collect() -> dict[str, Any]:
    report: dict[str, Any] = {
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "supported": sys.version_info >= MIN_PYTHON,
        },
        "platform": platform.platform(),
        "target_crawl4ai_version": TARGET_VERSION,
        "crawl4ai": {"installed": False, "version": None, "import_error": None},
        "playwright": {"installed": False, "import_error": None},
        "commands": {
            name: shutil.which(name)
            for name in ("crawl4ai-setup", "crawl4ai-doctor", "crwl", "playwright")
        },
        "writable_workdir": False,
        "ready_for_python_api": False,
    }

    try:
        module = importlib.import_module("crawl4ai")
        report["crawl4ai"]["installed"] = True
        report["crawl4ai"]["version"] = _module_version(module)
        required = ("AsyncWebCrawler", "BrowserConfig", "CrawlerRunConfig")
        report["crawl4ai"]["required_exports"] = {
            name: hasattr(module, name) for name in required
        }
    except Exception as exc:
        report["crawl4ai"]["import_error"] = f"{type(exc).__name__}: {exc}"

    try:
        importlib.import_module("playwright.async_api")
        report["playwright"]["installed"] = True
    except Exception as exc:
        report["playwright"]["import_error"] = f"{type(exc).__name__}: {exc}"

    try:
        probe = Path.cwd() / ".crawl4ai-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        report["writable_workdir"] = True
    except Exception:
        report["writable_workdir"] = False

    exports = report["crawl4ai"].get("required_exports", {})
    report["ready_for_python_api"] = bool(
        report["python"]["supported"]
        and report["crawl4ai"]["installed"]
        and report["playwright"]["installed"]
        and all(exports.values())
        and report["writable_workdir"]
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()
    report = collect()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Python: {report['python']['version']} (supported={report['python']['supported']})")
        print(
            "Crawl4AI: "
            f"installed={report['crawl4ai']['installed']} "
            f"version={report['crawl4ai']['version'] or 'unknown'}"
        )
        print(f"Playwright: installed={report['playwright']['installed']}")
        print(f"Ready: {report['ready_for_python_api']}")
        if report["crawl4ai"]["import_error"]:
            print(f"Crawl4AI import error: {report['crawl4ai']['import_error']}")
        if report["playwright"]["import_error"]:
            print(f"Playwright import error: {report['playwright']['import_error']}")

    return 0 if report["ready_for_python_api"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
