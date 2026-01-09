# sb2n

[![PyPI](
  <https://img.shields.io/pypi/v/sb2n?color=blue>
  )](
  <https://pypi.org/project/sb2n/>
) [![Release Package](
  <https://github.com/eggplants/sb2n/actions/workflows/release.yml/badge.svg>
  )](
  <https://github.com/eggplants/sb2n/actions/workflows/release.yml>
) [![CI](
  <https://github.com/eggplants/sb2n/actions/workflows/ci.yml/badge.svg>
  )](
  <https://github.com/eggplants/sb2n/actions/workflows/ci.yml>
)

Helpfeel Cosence (Scrapbox) to Notion Migration Tool

## Installation

```sh
pip install sb2n
# or, (use as CLI only)
pipx install sb2n
```

## Usage

### 1. Set up environment variables

Create a `.env` file in your project directory. (See: [`.env.example`](.env.example))

### 2. Prepare Notion Database

Create a database in Notion with the following properties:

- **Title** (Title) - Page title
- **Scrapbox URL** (URL) - Link to original Scrapbox page
- **Created Date** (Date) - Original creation date
- **Tags** (Multi-select) - Tags from Scrapbox

### 3. Run migration

```sh
# Basic migration
sb2n migrate

# Specify custom .env file
sb2n migrate --env-file /path/to/.env

# Dry run (no actual changes)
sb2n migrate --dry-run

# Migrate only first 10 pages
sb2n migrate -n 10

# Combine options: dry run with limit
sb2n migrate --dry-run -n 5

# Enable verbose logging
sb2n -v migrate
```

## Development

See [docs/specification.md](docs/specification.md) for detailed specifications.

## License

[MIT License](https://github.com/eggplants/sb2n/blob/master/LICENSE)
