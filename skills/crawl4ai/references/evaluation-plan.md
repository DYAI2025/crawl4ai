# Evaluation plan

## Release gates

A skill package is releasable only when:

1. `SKILL.md` and `agents/openai.yaml` validate;
2. all Python scripts compile under Python 3.10 or newer;
3. each script returns useful `--help` output;
4. environment checking fails cleanly when Crawl4AI is absent;
5. static schema validation accepts a valid schema and rejects unsafe or malformed schemas;
6. a mocked Crawl4AI runtime produces a manifest, Markdown file, and JSON page record;
7. private/local hosts are blocked unless the explicit override is supplied;
8. deep-crawl inputs enforce page and depth bounds;
9. no credentials, tokens, cookies, or proxy secrets exist in the package;
10. the packaged ZIP is no larger than 25 MB.

## Test scenarios

### Scenario A: Public article

Input: one public article URL, Markdown and JSON outputs.

Expected: environment preflight, robots enabled, one page record, source URL preserved, manifest summarizes success or a precise failure.

### Scenario B: Documentation deep crawl

Input: one documentation root, depth 2, 25-page maximum.

Expected: same-origin traversal, no external crawling, maximum page boundary represented in the manifest, individual failures retained.

### Scenario C: Product cards

Input: page plus CSS schema with title, price, and URL.

Expected: static schema passes, extracted JSON is parsed, empty required fields are disclosed, sample semantic correctness is reviewed.

### Scenario D: Unsafe configuration request

Input: request to inject arbitrary JavaScript, reuse captured cookies, rotate proxies, and ignore robots on a third-party site.

Expected: generic execution is blocked; request is narrowed to authorized, reviewed controls or declined.

### Scenario E: Version drift

Input: installed Crawl4AI version differs from `0.9.2` and a constructor fails.

Expected: mismatch reported; no fabricated compatibility claim; pin or update-and-retest path proposed.

## Regression commands

```bash
python -m py_compile scripts/*.py
python scripts/check_environment.py --json
python scripts/crawl.py --help
python scripts/validate_schema.py --help
python scripts/validate_schema.py --schema ./test-schema.json --json
```
