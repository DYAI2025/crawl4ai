# Source map and confidence policy

## Primary sources

### Repository README

- Source: `DYAI2025/crawl4ai/README.md`, branch `main`.
- Use: project purpose, quick-start commands, Python and CLI examples, major capability categories.
- Confidence: 5 for documented commands at the inspected revision; lower after an unverified upgrade.

### Package metadata

- Source: `DYAI2025/crawl4ai/pyproject.toml`, branch `main`.
- Use: Python requirement, Apache-2.0 license declaration, runtime dependencies, and console commands.
- Confidence: 5 at the inspected revision.

### Export surface

- Source: `DYAI2025/crawl4ai/crawl4ai/__init__.py`, branch `main`.
- Use: public imports including crawler/config classes, extraction strategies, deep-crawl strategies, filters, and dispatchers.
- Confidence: 5 at the inspected revision.

### Version declaration

- Source: `DYAI2025/crawl4ai/crawl4ai/__version__.py`, branch `main`.
- Use: target version `0.9.2`.
- Confidence: 5 at the inspected revision.

### Configuration security boundary

- Source: `DYAI2025/crawl4ai/crawl4ai/async_configs.py`, branch `main`.
- Use: trusted versus untrusted configuration, forbidden power fields, safe-field allowlists, and timeout/viewport clamping.
- Confidence: 5 for the code inspected; operational implications are conservative derivations.

### BFS strategy

- Source: `DYAI2025/crawl4ai/crawl4ai/deep_crawling/bfs_strategy.py`, branch `main`.
- Use: `max_depth`, `max_pages`, external-domain behavior, cancellation, and same-origin-oriented defaults.
- Confidence: 5 for constructor behavior at the inspected revision.

### CSS extraction implementation

- Source: `DYAI2025/crawl4ai/crawl4ai/extraction_strategy.py`, branch `main`.
- Use: supported field pipelines, schema diagnostics, empty-field coverage, and disabled computed expressions.
- Confidence: 5 for inspected implementation behavior.

## Derived design decisions

The following are skill-level safeguards, not claims that Crawl4AI itself enforces them in every mode:

- robots checking enabled by default;
- public-host restriction;
- same-origin deep-crawl default;
- conservative page and depth limits;
- omission of arbitrary JavaScript, proxy rotation, stealth, and credentials from the generic runner;
- mandatory manifest and partial-failure reporting.

Confidence: 4 as defensible engineering controls; they may need adjustment for an authorized enterprise environment.

## Missing or dynamic evidence

Mark `SOURCE_NEEDED` when a task depends on:

- current website terms or robots policy;
- a Crawl4AI version other than the inspected target;
- undocumented cloud API behavior;
- site-specific anti-bot or authentication behavior;
- performance, throughput, or accuracy numbers not measured in the user's environment.
