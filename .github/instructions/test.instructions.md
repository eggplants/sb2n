# sb2n プロジェクト - テストガイドライン

## テスト実行

### 基本コマンド

```bash
# 全テスト実行（最も一般的）
mise run pytest

# 詳細出力付き
mise run pytest -xvs

# 特定のテストファイルのみ
mise run pytest tests/test_parser.py

# 特定のテスト関数のみ
mise run pytest tests/test_parser.py::test_parse_internal_fragment_link -xvs

# カバレッジ計測
mise run pytest --cov=sb2n --cov-report=html
```

### テストファイル構成

```
tests/
├── test_parser.py        # パーサーのテスト（最重要）
├── test_migrator.py      # マイグレーションのテスト
├── test_link_restorer.py # リンク修復のテスト
└── test_sb2n.py          # 統合テスト
```

## テスト記述のガイドライン

### 1. パーサーテスト (test_parser.py)

新しい記法を追加した場合は必ずテストを追加してください。

**基本パターン**:

```python
def test_parse_new_feature() -> None:
    """Test description in English."""
    line = "[new syntax]"
    parsed = ScrapboxParser.parse_line(line)
    
    assert parsed.line_type == LineType.EXPECTED_TYPE
    assert parsed.content == "expected content"
```

**プロジェクト名が必要な場合**:

```python
def test_parse_internal_fragment_link() -> None:
    """Test internal link with fragment."""
    project_name = "myproject"
    
    line = "[PageTitle#section]"
    parsed = ScrapboxParser.parse_line(line, project_name)
    
    assert parsed.line_type == LineType.URL
    assert parsed.content == "https://scrapbox.io/myproject/PageTitle#section"
```

**複数行のテスト**:

```python
def test_parse_multiline_feature() -> None:
    """Test multiline parsing."""
    text = """page title
[line1]
 [line2]
  [line3]"""
    
    parsed_lines = ScrapboxParser.parse_text(text, "myproject")
    
    assert len(parsed_lines) == 3
    assert parsed_lines[0].line_type == LineType.EXPECTED_TYPE_1
    assert parsed_lines[1].line_type == LineType.EXPECTED_TYPE_2
```

### 2. エッジケースのテスト

必ず以下のエッジケースも確認してください:

- 空文字列
- 日本語/多バイト文字
- 特殊文字（`#`, `/`, `[`, `]` など）
- ネストした構造
- 境界値（最大/最小インデント、最長文字列など）

**例**:

```python
def test_parse_edge_cases() -> None:
    """Test edge cases."""
    # Empty string
    parsed = ScrapboxParser.parse_line("")
    assert parsed.line_type == LineType.PARAGRAPH
    
    # Japanese characters
    parsed = ScrapboxParser.parse_line("[ページ#セクション]", "myproject")
    assert "ページ" in parsed.content
    
    # Special characters
    parsed = ScrapboxParser.parse_line("[page#a/b/c]", "myproject")
    assert "#a/b/c" in parsed.content
```

### 3. リグレッションテスト

**重要**: 既存のテストは絶対に壊さないこと！

新機能を追加する際は、既存のテストが全てパスすることを確認してください:

```bash
# 実装前
mise run pytest  # すべてパスすることを確認

# 実装後
mise run pytest  # すべてパスすることを再確認
```

もし既存のテストが失敗する場合:
1. まず、仕様変更が意図的かどうか確認
2. 意図的な場合は、`docs/specification.md` を更新してテストを修正
3. 意図的でない場合は、実装を修正

### 4. テスト対象の優先度

パーサーテストが最も重要です（変換の起点のため）:

1. **最優先**: `test_parser.py` - すべての記法パターン
2. **高優先**: `test_link_restorer.py` - 内部リンク処理
3. **中優先**: `test_migrator.py` - マイグレーション制御
4. **低優先**: `test_sb2n.py` - E2Eテスト

## テスト記述のベストプラクティス

### Docstring は英語で

```python
def test_parse_heading() -> None:
    """Test heading parsing with different levels."""  # ✅ Good
    """見出しのパースをテスト"""  # ❌ Bad
```

### Arrange-Act-Assert パターン

```python
def test_example() -> None:
    """Test example."""
    # Arrange: テストデータの準備
    line = "[* Heading]"
    
    # Act: テスト対象の実行
    parsed = ScrapboxParser.parse_line(line)
    
    # Assert: 結果の検証
    assert parsed.line_type == LineType.HEADING_3
    assert parsed.content == "Heading"
```

### 1テスト1アサーション（原則）

複数の検証が必要な場合も、関連する検証はまとめて OK:

```python
def test_parse_icon() -> None:
    """Test icon notation."""
    line = "[/icons/hr.icon]"
    parsed = ScrapboxParser.parse_line(line)
    
    # 関連する検証はまとめてOK
    assert parsed.line_type == LineType.ICON
    assert parsed.icon_page_name == "hr"
    assert parsed.icon_project == "icons"
```

## モックの使用

外部 API（Scrapbox, Notion）を呼び出すテストでは、モックを使用してください:

```python
from unittest.mock import MagicMock, patch

def test_with_mock() -> None:
    """Test with mocked API."""
    mock_scrapbox = MagicMock()
    mock_scrapbox.project_name = "testproject"
    mock_scrapbox.get_page.return_value = {"title": "test"}
    
    # テスト実行
    result = some_function(mock_scrapbox)
    
    # モックが呼ばれたことを確認
    mock_scrapbox.get_page.assert_called_once_with("test")
```

## テスト失敗時のデバッグ

### 詳細出力で実行

```bash
mise run pytest tests/test_parser.py::test_failing -xvs
```

- `-x`: 最初のエラーで停止
- `-v`: 詳細出力
- `-s`: print デバッグを表示

### デバッグプリント

```python
def test_debug_example() -> None:
    """Test with debug output."""
    parsed = ScrapboxParser.parse_line("[test]")
    
    # デバッグ出力（-s オプション必要）
    print(f"DEBUG: {parsed.line_type=}")
    print(f"DEBUG: {parsed.content=}")
    
    assert parsed.line_type == LineType.EXPECTED
```

### pdb でデバッグ

```python
def test_with_pdb() -> None:
    """Test with debugger."""
    parsed = ScrapboxParser.parse_line("[test]")
    
    import pdb; pdb.set_trace()  # ここでブレークポイント
    
    assert parsed.line_type == LineType.EXPECTED
```

## テストカバレッジ

目標: **80%以上**

カバレッジレポートの確認:

```bash
mise run pytest --cov=sb2n --cov-report=html
# htmlcov/index.html をブラウザで開く
```

カバレッジが低い場合は、以下を追加:
- エッジケースのテスト
- エラーハンドリングのテスト
- 各分岐のテスト

## CI/CD での実行

現在 CI は未設定ですが、将来的には以下を想定:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: mise run pytest --cov=sb2n --cov-report=xml
  
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## チェックリスト

新機能実装時のテストチェックリスト:

- [ ] 基本的な動作のテストを追加した
- [ ] エッジケースのテストを追加した
- [ ] 日本語/多バイト文字のテストを追加した
- [ ] 既存の全テスト（57個）がパスする
- [ ] `mise run pytest -xvs` で詳細を確認した
- [ ] カバレッジが低下していない

## トラブルシューティング

### pytest が見つからない

```bash
# uvが正しくインストールされているか確認
mise exec -- python -m pytest --version

# または
mise run pytest --version
```

### テストが遅い

```bash
# 並列実行（pytest-xdist）
mise run pytest -n auto
```

### Import エラー

```bash
# PYTHONPATH を確認
export PYTHONPATH=/workspaces/sb2n:$PYTHONPATH
mise run pytest
```
