---
applyTo: "sb2n/**/*.py"
---
# sb2n プロジェクト - 基本開発ガイドライン

## 🚨 最重要ルール

**回答・実装の前に必ず [docs/specification.md](../../docs/specification.md) を確認すること**

- すべての機能仕様、実装方針、変換ルールが記載されています
- 実装時は必ず specification.md を読んで、既存の設計方針と矛盾しないか確認してください
- 新機能追加時は specification.md も併せて更新してください

## プロジェクト概要

Scrapboxのページを Notion または Markdown にエクスポートするCLIツール。

### 主要コマンド

```bash
# マイグレーション: Scrapbox → Notion
sb2n migrate [--icon] [-s/--skip] [--dry-run] [-n LIMIT]

# 内部リンク修復
sb2n restore-link

# エクスポート: Scrapbox → Markdown
sb2n export [-d OUTPUT_DIR] [--limit LIMIT]
```

### 開発環境

- **Python**: 3.14
- **パッケージマネージャ**: uv, mise
- **テストフレームワーク**: pytest
- **リンター/フォーマッター**: ruff

## プロジェクト構造

```
sb2n/
├── __init__.py
├── main.py              # CLIエントリーポイント
├── config.py            # 設定読み込み
├── parser.py            # Scrapbox記法パーサー ⭐
├── converter.py         # Notion変換ロジック ⭐
├── exporter.py          # Markdown変換ロジック
├── migrator.py          # マイグレーション制御
├── link_restorer.py     # 内部リンク修復
├── notion_service.py    # Notion API ラッパー
├── scrapbox_service.py  # Scrapbox API ラッパー
└── models/
    ├── blocks.py        # Notionブロックモデル
    └── pages.py         # Notionページモデル
```

### 主要モジュールの役割

#### parser.py（パーサー）
- Scrapbox記法を `ParsedLine` に変換
- 正規表現パターンによるパターンマッチング
- `LineType` enum で行種別を判定
- **重要**: 静的メソッド、プロジェクト名はオプション引数で渡す

```python
parsed_lines = ScrapboxParser.parse_text(text, project_name="myproject")
```

#### converter.py（Notion変換）
- `ParsedLine` を Notion ブロックに変換
- リストのネスト処理（最大2階層）
- アイコン変換（`--icon` フラグ時）
- **制限**: Notion API はリストのネストを2階層までしか許容しない

#### exporter.py（Markdown変換）
- `ParsedLine` を Markdown に変換
- 画像を `assets/` ディレクトリにダウンロード
- 背景色は HTML `<span>` タグで表現

## コーディング規約

### 型ヒント

必ず型ヒントを使用してください：

```python
def parse_line(line: str, project_name: str | None = None) -> ParsedLine:
    """Parse a single line."""
    ...
```

### パターン追加時の注意

新しいパターンを追加する場合:

1. `parser.py` の `ScrapboxParser` クラスにパターンを追加
2. `parse_line()` または `parse_text()` に処理ロジックを追加
3. `converter.py` または `exporter.py` に変換ロジックを追加
4. **必ずテストを追加** (`tests/test_parser.py` など)
5. **specification.md を更新**

### Notion API の制限事項

- **リストのネスト**: 最大2階層（合計3階層）まで
- **ブロック追加**: 一度に100ブロックまで
- **レート制限**: 秒間3リクエスト

これらの制限を考慮した実装を心がけてください。

## テストの実行

```bash
# 全テストを実行
mise run pytest

# 特定のテストを実行
mise run pytest tests/test_parser.py::test_parse_internal_fragment_link -xvs

# カバレッジ付き
mise run pytest --cov=sb2n --cov-report=html
```

## 実装時のチェックリスト

- [ ] `docs/specification.md` を確認した
- [ ] 既存の設計パターンに従っている
- [ ] 型ヒントを適切に使用している
- [ ] テストを追加/更新した（全テストがパスすること）
- [ ] specification.md を更新した（新機能の場合）
- [ ] Notion API の制限を考慮している

## よくある実装パターン

### 新しい記法の追加

1. **パターン定義** (parser.py):
```python
NEW_PATTERN = re.compile(r"^\[新しいパターン\]$")
```

2. **パース処理** (parser.py):
```python
if match := ScrapboxParser.NEW_PATTERN.match(stripped):
    return ParsedLine(
        original=line,
        line_type=LineType.NEW_TYPE,
        content=match.group(1),
    )
```

3. **変換処理** (converter.py):
```python
if parsed_line.line_type == LineType.NEW_TYPE:
    return self.notion_service.create_some_block(parsed_line.content)
```

4. **テスト追加** (tests/test_parser.py):
```python
def test_parse_new_pattern() -> None:
    line = "[新しいパターン]"
    parsed = ScrapboxParser.parse_line(line)
    assert parsed.line_type == LineType.NEW_TYPE
```

## デバッグのヒント

### パーサーのデバッグ

```python
from sb2n.parser import ScrapboxParser

text = """test page
[Page#section]
"""
parsed = ScrapboxParser.parse_text(text, "myproject")
for line in parsed:
    print(f"{line.line_type}: {line.content}")
```

### ログレベルの変更

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 参考リンク

- [Scrapbox記法リファレンス](https://scrapbox.io/help-jp/%E8%A8%98%E6%B3%95)
- [Notion API ドキュメント](https://developers.notion.com/)
- [scrapbox-client](https://pypi.org/project/scrapbox-client/)
- [notion-client](https://pypi.org/project/notion-client/)
