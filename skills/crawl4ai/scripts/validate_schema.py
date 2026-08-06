#!/usr/bin/env python3
"""Validate a Crawl4AI JsonCssExtractionStrategy schema.

Static validation works without Crawl4AI. With --html and Crawl4AI installed,
the script also runs the repository's extraction-schema diagnostic.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ALLOWED_TYPES = {
    "text",
    "attribute",
    "html",
    "regex",
    "nested",
    "list",
    "nested_list",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Schema file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("Schema root must be a JSON object.")
    return data


def validate_field(field: Any, path: str, issues: list[str]) -> None:
    if not isinstance(field, dict):
        issues.append(f"{path} must be an object")
        return
    name = field.get("name")
    if not isinstance(name, str) or not name.strip():
        issues.append(f"{path}.name must be a non-empty string")

    field_type = field.get("type")
    pipeline = field_type if isinstance(field_type, list) else [field_type]
    if not pipeline or any(step not in ALLOWED_TYPES for step in pipeline):
        issues.append(f"{path}.type contains unsupported values: {field_type!r}")

    if "attribute" in pipeline and not isinstance(field.get("attribute"), str):
        issues.append(f"{path}.attribute is required for attribute extraction")
    if "regex" in pipeline and not isinstance(field.get("pattern"), str):
        issues.append(f"{path}.pattern is required for regex extraction")
    if field_type in {"nested", "list", "nested_list"}:
        if not isinstance(field.get("selector"), str) or not field["selector"].strip():
            issues.append(f"{path}.selector is required for {field_type}")
        nested = field.get("fields")
        if not isinstance(nested, list) or not nested:
            issues.append(f"{path}.fields must be a non-empty list for {field_type}")
        else:
            for index, child in enumerate(nested):
                validate_field(child, f"{path}.fields[{index}]", issues)

    if "expression" in field:
        issues.append(f"{path}.expression is blocked; executable computed expressions are unsafe")
    if "function" in field:
        issues.append(f"{path}.function cannot be represented safely in JSON schemas")


def static_validate(schema: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    base_selector = schema.get("baseSelector")
    if not isinstance(base_selector, str) or not base_selector.strip():
        issues.append("baseSelector must be a non-empty string")

    fields = schema.get("fields")
    if not isinstance(fields, list) or not fields:
        issues.append("fields must be a non-empty list")
    else:
        names: list[str] = []
        for index, field in enumerate(fields):
            validate_field(field, f"fields[{index}]", issues)
            if isinstance(field, dict) and isinstance(field.get("name"), str):
                names.append(field["name"])
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            issues.append(f"duplicate field names: {', '.join(duplicates)}")
    return issues


def runtime_validate(schema: dict[str, Any], html_path: Path, expected: list[str]) -> dict[str, Any]:
    try:
        from crawl4ai import JsonCssExtractionStrategy
    except Exception as exc:
        return {
            "success": False,
            "issues": [f"Crawl4AI runtime unavailable: {type(exc).__name__}: {exc}"],
        }
    html = html_path.read_text(encoding="utf-8")
    return JsonCssExtractionStrategy._validate_schema(
        schema=schema,
        html_content=html,
        schema_type="CSS",
        expected_fields=expected or None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--html", type=Path, help="Optional local HTML fixture for runtime validation.")
    parser.add_argument("--expected-field", action="append", default=[])
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    args = parser.parse_args()

    try:
        schema = load_json(args.schema)
        static_issues = static_validate(schema)
    except ValueError as exc:
        report = {"success": False, "static_issues": [str(exc)], "runtime": None}
        print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else str(exc))
        return 2

    runtime = None
    if args.html:
        try:
            runtime = runtime_validate(schema, args.html, args.expected_field)
        except Exception as exc:
            runtime = {"success": False, "issues": [f"Runtime validation failed: {type(exc).__name__}: {exc}"]}

    success = not static_issues and (runtime is None or bool(runtime.get("success")))
    report = {"success": success, "static_issues": static_issues, "runtime": runtime}
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        print("Schema valid." if success else "Schema validation failed.")
        for issue in static_issues:
            print(f"- {issue}")
        if runtime is not None:
            print(json.dumps(runtime, indent=2, ensure_ascii=False, default=str))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
