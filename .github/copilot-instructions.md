# sb2n - AI Agent Instructions

## Project Overview

**sb2n** is a CLI tool to migrate [Helpfeel Cosense (Scrapbox)](https://cosen.se/) pages to [Notion](https://www.notion.com/) and export them to Markdown.

- Python 3.14, package manager: `uv` + `mise`
- Key commands: `sb2n migrate`, `sb2n restore-link`, `sb2n export`

## Essential References

Always read [docs/specification.md](../docs/specification.md) **before** implementing or reviewing anything. It defines all conversion rules, Notion API constraints, and architecture decisions.

- Scrapbox syntax: [docs/scrapbox-syntax-spec.md](../docs/scrapbox-syntax-spec.md)
- Scrapbox syntax reference: [docs/scrapbox-syntax-reference.md](../docs/scrapbox-syntax-reference.md)

## Development Commands

```bash
mise run pytest          # run all tests
mise run pytest -xvs     # verbose, stop on first failure
mise run ty              # type check (uvx ty)
mise run ruff            # format with ruff
mise run ci              # full CI: format + typecheck + lint + tests
```

## Architecture

```
parser.py      → ScrapboxParser: text → ParsedLine[]
converter.py   → NotionConverter: ParsedLine[] → Notion blocks
exporter.py    → MarkdownExporter: ParsedLine[] → Markdown
migrator.py    → Migrator: orchestrates migration flow
notion_service.py / scrapbox_service.py → API wrappers
models/blocks.py, models/pages.py       → Pydantic models
```

**Module boundary rule**: `parser.py` parses only. `converter.py` is Notion-only. `exporter.py` is Markdown-only.

## Key Constraints

- Notion API: list nesting max 2 levels deep; max 100 blocks per append; rate limit 3 req/s
- When adding a new Scrapbox syntax: update `parser.py` → `converter.py`/`exporter.py` → tests → `docs/specification.md`

## Coding Conventions

- All functions/methods must have type hints and English docstrings (Google style)
- Constant names: `UPPER_CASE`; no romanized Japanese variable names
- Line length: 120 chars; quotes: double; linter: ruff (all rules, see `pyproject.toml`)
- Tests use `pytest`; test files in `tests/test_*.py`; no docstrings required in test functions

## Detailed Guidelines

- Implementation: [.github/instructions/basic.instructions.md](instructions/basic.instructions.md)
- Code review: [.github/instructions/review.instructions.md](instructions/review.instructions.md)
- Testing: [.github/instructions/test.instructions.md](instructions/test.instructions.md)
