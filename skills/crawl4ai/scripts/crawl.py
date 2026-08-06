#!/usr/bin/env python3
"""Run bounded Crawl4AI crawls and write auditable output files."""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import re
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

TARGET_VERSION = "0.9.2"
PRIVATE_HOST_PATTERNS = (
    re.compile(r"^localhost$", re.I),
    re.compile(r"^127\."),
    re.compile(r"^10\."),
    re.compile(r"^192\.168\."),
    re.compile(r"^172\.(1[6-9]|2\d|3[01])\."),
    re.compile(r"^169\.254\."),
    re.compile(r"^\[?::1\]?$")
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    urls = parser.add_mutually_exclusive_group(required=True)
    urls.add_argument("--url", action="append", help="HTTP(S) URL. Repeat for multiple URLs.")
    urls.add_argument("--urls-file", type=Path, help="UTF-8 file with one URL per line.")
    parser.add_argument("--output-dir", type=Path, default=Path("crawl-output"))
    parser.add_argument("--formats", default="markdown,json", help="Comma-separated: markdown,json,html")
    parser.add_argument("--deep", action="store_true", help="Enable bounded BFS deep crawling.")
    parser.add_argument("--max-depth", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--include-external", action="store_true")
    parser.add_argument("--schema", type=Path, help="JsonCssExtractionStrategy schema JSON.")
    parser.add_argument("--css-selector")
    parser.add_argument("--wait-for", help="CSS selector or Crawl4AI wait condition.")
    parser.add_argument("--scan-full-page", action="store_true")
    parser.add_argument("--screenshot", action="store_true")
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument("--word-count-threshold", type=int, default=10)
    parser.add_argument("--page-timeout", type=int, default=60000, help="Milliseconds, capped at 120000.")
    parser.add_argument("--cache-mode", choices=("enabled", "bypass", "disabled", "read_only", "write_only"), default="bypass")
    parser.add_argument("--ignore-robots", action="store_true")
    parser.add_argument("--browser-type", choices=("chromium", "firefox", "webkit"), default="chromium")
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--text-mode", action="store_true")
    parser.add_argument("--allow-private-hosts", action="store_true", help="Only for user-controlled local test environments.")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def read_urls(args: argparse.Namespace) -> list[str]:
    values = list(args.url or [])
    if args.urls_file:
        values = [
            line.strip()
            for line in args.urls_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    if not values:
        raise ValueError("No URLs supplied.")
    return values


def validate_url(value: str, allow_private: bool) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Unsupported URL: {value!r}; only absolute HTTP(S) URLs are accepted.")
    host = parsed.hostname
    if not allow_private and any(pattern.search(host) for pattern in PRIVATE_HOST_PATTERNS):
        raise ValueError(f"Private or local host blocked by default: {host}")
    return value


def load_schema(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("baseSelector") or not isinstance(data.get("fields"), list):
        raise ValueError("Schema must be an object with baseSelector and fields.")
    return data


def cache_mode_value(CacheMode: Any, name: str) -> Any:
    candidates = {
        "enabled": ("ENABLED",),
        "bypass": ("BYPASS",),
        "disabled": ("DISABLED",),
        "read_only": ("READ_ONLY",),
        "write_only": ("WRITE_ONLY",),
    }[name]
    for candidate in candidates:
        if hasattr(CacheMode, candidate):
            return getattr(CacheMode, candidate)
    raise RuntimeError(f"Installed Crawl4AI does not expose CacheMode for {name!r}.")


def safe_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [safe_json(v) for v in value]
    if is_dataclass(value):
        return safe_json(asdict(value))
    if hasattr(value, "model_dump"):
        try:
            return safe_json(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        return {
            str(k): safe_json(v)
            for k, v in vars(value).items()
            if not str(k).startswith("_")
        }
    return str(value)


def markdown_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    for attr in ("raw_markdown", "fit_markdown", "markdown_with_citations"):
        candidate = getattr(value, attr, None)
        if isinstance(candidate, str) and candidate:
            return candidate
    return str(value)


def parse_extracted(value: Any) -> Any:
    if not isinstance(value, str):
        return safe_json(value)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def file_stem(url: str, index: int) -> str:
    parsed = urlparse(url)
    raw = f"{parsed.netloc}{parsed.path}".strip("/") or parsed.netloc
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip("-")[:80] or "page"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
    return f"{index:04d}-{slug}-{digest}"


def write_binary(value: Any, path: Path) -> bool:
    if value is None:
        return False
    if isinstance(value, bytes):
        path.write_bytes(value)
        return True
    if isinstance(value, str):
        try:
            path.write_bytes(base64.b64decode(value, validate=True))
            return True
        except Exception:
            return False
    return False


def normalize_results(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes, dict)):
        try:
            return list(value)
        except TypeError:
            pass
    return [value]


def result_record(result: Any, stem: str, output_dir: Path, formats: set[str]) -> dict[str, Any]:
    url = str(getattr(result, "url", ""))
    success = bool(getattr(result, "success", False))
    markdown = markdown_text(getattr(result, "markdown", None))
    extracted = parse_extracted(getattr(result, "extracted_content", None))
    files: dict[str, str] = {}

    if "markdown" in formats:
        path = output_dir / f"{stem}.md"
        path.write_text(markdown, encoding="utf-8")
        files["markdown"] = str(path)
    if "html" in formats:
        html = getattr(result, "cleaned_html", None) or getattr(result, "html", None) or ""
        path = output_dir / f"{stem}.html"
        path.write_text(str(html), encoding="utf-8")
        files["html"] = str(path)
    if write_binary(getattr(result, "screenshot", None), output_dir / f"{stem}.png"):
        files["screenshot"] = str(output_dir / f"{stem}.png")
    pdf_value = getattr(result, "pdf", None) or getattr(result, "pdf_bytes", None)
    if write_binary(pdf_value, output_dir / f"{stem}.pdf"):
        files["pdf"] = str(output_dir / f"{stem}.pdf")

    record = {
        "url": url,
        "success": success,
        "status_code": getattr(result, "status_code", None),
        "error_message": getattr(result, "error_message", None),
        "metadata": safe_json(getattr(result, "metadata", None)),
        "links": safe_json(getattr(result, "links", None)),
        "extracted_content": extracted,
        "markdown_characters": len(markdown),
        "files": files,
    }
    if "json" in formats:
        path = output_dir / f"{stem}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        files["json"] = str(path)
    return record


async def execute(args: argparse.Namespace, urls: list[str], schema: dict[str, Any] | None) -> tuple[str | None, list[Any]]:
    try:
        import crawl4ai
        from crawl4ai import (
            AsyncWebCrawler,
            BFSDeepCrawlStrategy,
            BrowserConfig,
            CacheMode,
            CrawlerRunConfig,
            JsonCssExtractionStrategy,
        )
    except Exception as exc:
        raise RuntimeError(
            "Crawl4AI is not importable. Run scripts/check_environment.py and install the runtime first. "
            f"Original error: {type(exc).__name__}: {exc}"
        ) from exc

    version = getattr(crawl4ai, "__version__", None)
    if not isinstance(version, str):
        try:
            from crawl4ai.__version__ import __version__ as version
        except Exception:
            version = None

    browser_config = BrowserConfig(
        browser_type=args.browser_type,
        headless=not args.headful,
        text_mode=args.text_mode,
        verbose=args.verbose,
    )
    run_kwargs: dict[str, Any] = {
        "word_count_threshold": max(0, args.word_count_threshold),
        "css_selector": args.css_selector,
        "wait_for": args.wait_for,
        "scan_full_page": args.scan_full_page,
        "screenshot": args.screenshot,
        "pdf": args.pdf,
        "page_timeout": max(1000, min(args.page_timeout, 120000)),
        "cache_mode": cache_mode_value(CacheMode, args.cache_mode),
        "check_robots_txt": not args.ignore_robots,
        "verbose": args.verbose,
    }
    if schema is not None:
        run_kwargs["extraction_strategy"] = JsonCssExtractionStrategy(schema=schema)
    if args.deep:
        run_kwargs["deep_crawl_strategy"] = BFSDeepCrawlStrategy(
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            include_external=args.include_external,
        )
    config = CrawlerRunConfig(**run_kwargs)

    all_results: list[Any] = []
    async with AsyncWebCrawler(config=browser_config) as crawler:
        if args.deep:
            for url in urls:
                all_results.extend(normalize_results(await crawler.arun(url=url, config=config)))
        elif len(urls) == 1:
            all_results.extend(normalize_results(await crawler.arun(url=urls[0], config=config)))
        else:
            all_results.extend(normalize_results(await crawler.arun_many(urls=urls, config=config)))
    return version, all_results


def main() -> int:
    args = parse_args()
    try:
        urls = [validate_url(url, args.allow_private_hosts) for url in read_urls(args)]
        if args.max_depth < 0 or args.max_depth > 10:
            raise ValueError("--max-depth must be between 0 and 10.")
        if args.max_pages < 1 or args.max_pages > 1000:
            raise ValueError("--max-pages must be between 1 and 1000.")
        if args.include_external and not args.deep:
            raise ValueError("--include-external requires --deep.")
        schema = load_schema(args.schema)
        formats = {value.strip().lower() for value in args.formats.split(",") if value.strip()}
        unsupported = formats - {"markdown", "json", "html"}
        if unsupported or not formats:
            raise ValueError(f"Unsupported or empty --formats value: {sorted(unsupported)}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    try:
        version, results = asyncio.run(execute(args, urls, schema))
    except Exception as exc:
        print(f"Execution error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    records = [
        result_record(result, file_stem(str(getattr(result, "url", urls[0])), index), args.output_dir, formats)
        for index, result in enumerate(results, start=1)
    ]
    succeeded = sum(1 for record in records if record["success"])
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": (datetime.now(timezone.utc) - started).total_seconds(),
        "target_skill_version": TARGET_VERSION,
        "detected_crawl4ai_version": version,
        "request": {
            "seed_urls": urls,
            "deep": args.deep,
            "max_depth": args.max_depth if args.deep else None,
            "max_pages": args.max_pages if args.deep else None,
            "include_external": args.include_external,
            "robots_checked": not args.ignore_robots,
            "schema": str(args.schema) if args.schema else None,
            "formats": sorted(formats),
        },
        "summary": {
            "results": len(records),
            "succeeded": succeeded,
            "failed": len(records) - succeeded,
        },
        "pages": records,
    }
    manifest_path = args.output_dir / "crawl-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), **manifest["summary"]}, ensure_ascii=False))
    return 0 if records and succeeded == len(records) else 4


if __name__ == "__main__":
    raise SystemExit(main())
