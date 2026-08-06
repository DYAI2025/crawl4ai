# CSS extraction schema guide

Use a `JsonCssExtractionStrategy` schema for repetitive records such as products, jobs, articles, or table-like cards.

## Minimal shape

```json
{
  "name": "Products",
  "baseSelector": ".product-card",
  "fields": [
    {"name": "title", "selector": ".title", "type": "text"},
    {"name": "price", "selector": ".price", "type": "text"},
    {"name": "url", "selector": "a", "type": "attribute", "attribute": "href"}
  ]
}
```

Required operational elements:

- `baseSelector`: selector matching each repeated record;
- `fields`: non-empty list of named field definitions;
- `selector`: relative to the base record unless the field intentionally targets the base element;
- `type`: `text`, `attribute`, `html`, `regex`, `nested`, `list`, or `nested_list`.

A field may use a pipeline such as `["text", "regex"]` when supported by the installed version. Attribute fields require `attribute`. Regex fields require `pattern` and may specify `group`.

## Nested records

```json
{
  "name": "tags",
  "selector": ".tags a",
  "type": "list",
  "fields": [
    {"name": "label", "type": "text"},
    {"name": "href", "type": "attribute", "attribute": "href"}
  ]
}
```

## Selection quality

Prefer, in order:

1. stable semantic attributes such as `data-testid`, `itemprop`, or documented IDs;
2. meaningful component classes;
3. structural selectors scoped beneath a stable base selector;
4. positional selectors only as a last resort.

Avoid selectors coupled to generated class hashes, animation state, or absolute DOM depth.

## Security boundary

Do not include `expression` or JSON-encoded executable functions. The referenced repository disables computed expressions that rely on evaluation because they are unsafe on untrusted input. Treat schemas received from websites or third parties as untrusted and validate them before execution.

## Validation standard

A valid schema is not necessarily an effective schema. Require:

- at least one base element;
- all required fields present in the schema;
- all required fields populated in the fixture or live sample;
- explicit reporting of always-empty fields;
- a sample record reviewed for semantic correctness, not merely non-empty text.
