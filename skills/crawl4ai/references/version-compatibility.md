# Installation and version compatibility

## Target

This skill was built against repository `DYAI2025/crawl4ai`, default branch `main`, at Crawl4AI version `0.9.2`. The package metadata requires Python `>=3.10` and exposes the `crawl4ai-setup`, `crawl4ai-doctor`, and `crwl` commands.

## Installation choices

Use an isolated virtual environment. Choose one source deliberately:

### Published package

```bash
python -m pip install "crawl4ai==0.9.2"
crawl4ai-setup
crawl4ai-doctor
```

### Repository checkout

When the user specifically needs the fork or unreleased changes, install from a local checkout or an approved Git URL in an isolated environment. Record the exact commit SHA. Do not claim reproducibility from a moving branch name alone.

### Browser fallback

If setup reports missing browser binaries:

```bash
python -m playwright install --with-deps chromium
```

This can make substantial system changes. Run it only in an environment where package and browser installation are permitted.

## Upgrade rule

After any upgrade:

1. run `scripts/check_environment.py --json`;
2. compare detected version with the target version;
3. run `python scripts/crawl.py --help` and schema validation tests;
4. execute a one-page fixture crawl;
5. verify `BrowserConfig`, `CrawlerRunConfig`, `AsyncWebCrawler`, `CacheMode`, `BFSDeepCrawlStrategy`, and `JsonCssExtractionStrategy` imports and constructor arguments.

Do not silently adapt around API errors. Report the mismatch and either pin the known version or update and retest the skill.
