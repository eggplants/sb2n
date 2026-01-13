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

[Helpfeel Cosense (Scrapbox)](https://cosen.se/) to [Notion](https://www.notion.com/) Migration Tool

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

![Screenshot](https://github.com/user-attachments/assets/b26cbfb5-fa66-4f08-a5b9-faa30d6303e1)

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

# Skip pages that already exist in Notion
sb2n migrate --skip-existing

# Combine options: dry run with limit and skip existing
sb2n migrate --dry-run -n 5 --skip-existing

# Enable verbose logging
sb2n -v migrate
```

### 4. Restore internal links

After migration, restore [Scrapbox internal links](https://scrapbox.io/help-jp/ページをリンクする) (`[PageName]` format) to actual [Notion page mentions](https://www.notion.com/help/create-links-and-backlinks#inline-in-a-paragraph):

```sh
# Restore links in all pages
sb2n restore-link

# Dry run (preview changes without applying)
sb2n restore-link --dry-run

# Restore links in specific pages only
sb2n restore-link --pages "HomePage,Getting Started"

# Enable verbose logging
sb2n -v restore-link
```

## Appendix 1. Export as Markdown with images

Export Scrapbox pages to Markdown format with downloaded images. Images are saved in an `assets/` directory and referenced with relative paths in the Markdown files.

### Usage

```sh
# Export to default directory (./out)
sb2n export

# Specify output directory
sb2n export -d /path/to/output

# Limit number of pages to export
sb2n export --limit 10

# Combine options
sb2n export -d ./my-export --limit 5

# Enable verbose logging
sb2n -v export
```

### Options

- `--env-file PATH` - Path to .env file (default: `.env`)
- `-d, --output-dir DIR` - Output directory for exported files (default: `./out`)
- `--limit N` - Limit the number of pages to export
- `-v, --verbose` - Enable verbose logging

### Output Structure

```text
output-dir/
├── assets/              # Downloaded images
│   ├── abc123def456.png
│   ├── 789ghijk012.jpg
│   └── ...
├── page1.md            # Markdown files
├── page2.md
└── ...
```

### Conversion Rules

| Scrapbox Notation | Markdown Output |
| ----------------- | --------------- |
| `[* Heading]` | `## Heading` |
| `[** Heading]` | `### Heading` |
| `[*** Heading]` | `#### Heading` |
| `[[Bold]]` | `**Bold**` |
| `[/ Italic]` | `*Italic*` |
| `[- Strikethrough]` | `~~Strikethrough~~` |
| `[_ Underline]` | `<u>Underline</u>` |
| `` `Code` `` | `` `Code` `` |
| `[! Red background]` | `<span style="background-color: #ffebee">Red background</span>` |
| `[# Green background]` | `<span style="background-color: #e8f5e9">Green background</span>` |
| `[% Blue background]` | `<span style="background-color: #e3f2fd">Blue background</span>` |
| `[Image URL]` | `![image](assets/xxx.png)` |
| `[Link text URL]` | `[Link text](URL)` |
| `[/project/page]` | `[https://scrapbox.io/project/page](https://scrapbox.io/project/page)` |
| List item | `- List item` |
| `> Quote` | `> Quote` |
| `code:python` | ` ```python ` |

### Important Notes

1. **Image Download**: All images from Scrapbox (including external URLs) are downloaded and saved to the `assets/` directory
2. **Filename**: Page titles become filenames. Special characters are replaced with `_`
3. **Relative Links**: Image references in Markdown use relative paths (`assets/xxx.png`)
4. **No Notion Required**: This command only uses the Scrapbox API and does not require Notion configuration

## Development

See [docs/specification.md](docs/specification.md) for detailed specifications.

## License

[MIT License](https://github.com/eggplants/sb2n/blob/master/LICENSE)
