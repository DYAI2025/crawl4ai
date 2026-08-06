# Crawl4AI operating patterns

## Contents

1. Preflight
2. Single-page crawl
3. Batch crawl
4. Deep crawl
5. Structured extraction
6. Dynamic pages
7. Outputs and failure handling

## 1. Preflight

Run:

```bash
python scripts/check_environment.py --json
```

A nonzero exit means the runtime is incomplete. The checker is read-only. Installation is an explicit separate action because package and browser installation can modify the environment substantially.

## 2. Single-page crawl

```bash
python scripts/crawl.py \
  --url "https://example.com/article" \
  --formats markdown,json \
  --output-dir ./crawl-output
```

Use `--css-selector main` to limit content when the page has a stable main container. Do not guess selectors when a failed crawl can first expose the page structure.

## 3. Batch crawl

Repeat `--url`:

```bash
python scripts/crawl.py \
  --url "https://example.com/a" \
  --url "https://example.com/b" \
  --output-dir ./crawl-output
```

Or supply one URL per line:

```bash
python scripts/crawl.py --urls-file ./urls.txt --output-dir ./crawl-output
```

## 4. Deep crawl

```bash
python scripts/crawl.py \
  --url "https://docs.example.com" \
  --deep --max-depth 2 --max-pages 25 \
  --output-dir ./crawl-output
```

The wrapper defaults to same-origin traversal. Add `--include-external` only when the scope explicitly includes third-party domains. Page limits are total safeguards, not promises that every page will be reachable.

## 5. Structured extraction

A CSS schema is deterministic and preferable to LLM extraction for repetitive page structures.

```bash
python scripts/validate_schema.py --schema ./products.schema.json --json
python scripts/crawl.py \
  --url "https://example.com/products" \
  --schema ./products.schema.json \
  --formats json,markdown \
  --output-dir ./crawl-output
```

When a local HTML fixture is available:

```bash
python scripts/validate_schema.py \
  --schema ./products.schema.json \
  --html ./fixture.html \
  --expected-field title \
  --expected-field price \
  --json
```

## 6. Dynamic pages

Prefer the smallest intervention:

```bash
python scripts/crawl.py \
  --url "https://example.com/app" \
  --wait-for "css:.results" \
  --output-dir ./crawl-output
```

Use `--scan-full-page` only for pages that load content during scrolling. It increases execution time and resource use. The wrapper intentionally omits arbitrary JavaScript, cookies, proxy rotation, and stealth controls; those require case-specific authorization and code review.

## 7. Outputs and failure handling

The output directory contains:

- `crawl-manifest.json`: request scope, detected version, counts, page records, and output paths;
- one `.md` file per result when Markdown is requested;
- one `.json` record per result when JSON is requested;
- optional `.html`, `.png`, or `.pdf` files.

Exit codes:

- `0`: every emitted page result succeeded;
- `2`: invalid input or blocked target scope;
- `3`: environment or execution failure before result processing;
- `4`: partial or complete page failure.

Treat an empty result set, zero extracted fields, timeout, robots denial, or HTTP authorization failure as a failed or incomplete operation, even when some files were created.
