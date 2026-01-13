# sb2n プロジェクト - コードレビューガイドライン

## 🚨 レビュー前の必須確認事項

1. **[docs/specification.md](../../docs/specification.md) との整合性を確認**
   - 実装が仕様書の記載と一致しているか
   - 新機能の場合、specification.md が更新されているか

2. **全テストがパスしているか**
   ```bash
   mise run pytest
   ```
   - 既存のテスト（または現在のテスト数）が全てパスすること
   - 新機能には新しいテストが追加されていること

3. **型ヒントが正しく使用されているか**
   - すべての関数・メソッドに型ヒントがあること
   - `str | None` などの Union 型が適切に使われていること

## レビューチェックリスト

### 1. 設計・アーキテクチャ

#### specification.md との整合性
- [ ] 実装が specification.md の方針に従っているか
- [ ] 変換ルールが specification.md に記載されているか
- [ ] 新機能の場合、specification.md が更新されているか

#### 既存パターンの踏襲
- [ ] 既存の `LineType` を適切に使用しているか
- [ ] `ParsedLine` の構造を正しく使っているか
- [ ] パーサー → コンバーター → サービス の流れに従っているか

#### モジュール境界
- [ ] `parser.py` はパースのみを行っているか（変換ロジックが入っていないか）
- [ ] `converter.py` は Notion 固有のロジックのみか
- [ ] `exporter.py` は Markdown 固有のロジックのみか

### 2. コード品質

#### 型安全性
- [ ] すべての関数に型ヒントがあるか
- [ ] 戻り値の型が明示されているか
- [ ] `None` チェックが適切に行われているか

```python
# ✅ Good
def parse_line(line: str, project_name: str | None = None) -> ParsedLine:
    if project_name:
        # project_name を使う処理
        pass

# ❌ Bad
def parse_line(line, project_name=None):
    # 型ヒントなし
```

#### 命名規則
- [ ] 変数名・関数名が分かりやすいか
- [ ] 英語の命名規則に従っているか（ローマ字は NG）
- [ ] 定数は `UPPER_CASE` で定義されているか

```python
# ✅ Good
INTERNAL_FRAGMENT_LINK_PATTERN = re.compile(...)
def parse_internal_fragment_link(line: str) -> ParsedLine:

# ❌ Bad
naibu_link_pattern = re.compile(...)  # ローマ字
def p(l):  # 略称すぎる
```

#### Docstring
- [ ] すべての public 関数・クラスに docstring があるか
- [ ] docstring は英語で記述されているか
- [ ] 引数と戻り値が説明されているか

```python
# ✅ Good
def parse_line(line: str, project_name: str | None = None) -> ParsedLine:
    """Parse a single line of Scrapbox text.

    Args:
        line: Line to parse
        project_name: Optional Scrapbox project name for internal fragment links

    Returns:
        Parsed line with type and content
    """

# ❌ Bad
def parse_line(line, project_name=None):
    # docstring なし
```

### 3. パーサー実装（parser.py）

#### パターンマッチング
- [ ] 正規表現パターンが適切か
- [ ] パターンの優先順位が正しいか（特定的なパターンから先にチェック）
- [ ] エッジケースを考慮しているか

```python
# ✅ Good: 特定的なパターンを先にチェック
if icon_match := ICON_PATTERN.match(stripped):
    # アイコンとして処理
elif cross_project_match := CROSS_PROJECT_LINK_PATTERN.match(stripped):
    # クロスプロジェクトリンクとして処理
elif internal_fragment_match := INTERNAL_FRAGMENT_LINK_PATTERN.match(stripped):
    # 内部フラグメントリンクとして処理
```

#### インデント処理
- [ ] インデントレベルの計算が正しいか
- [ ] コードブロックのインデント除去が適切か
- [ ] リストのネストレベルが考慮されているか

### 4. コンバーター実装（converter.py, exporter.py）

#### Notion API 制限の考慮
- [ ] リストのネストが2階層以内に制限されているか
- [ ] ブロック追加が100個以内に制限されているか（バッチ処理の場合）
- [ ] レート制限を考慮しているか

```python
# ✅ Good: ネストレベルを制限
effective_indent = min(parsed_line.indent_level, 2)
```

#### エラーハンドリング
- [ ] API エラーが適切に処理されているか
- [ ] ログ出力が適切か
- [ ] ユーザーにわかりやすいエラーメッセージが出力されるか

```python
# ✅ Good
try:
    notion_service.create_page(...)
except Exception as e:
    logger.error("Failed to create page: %s", e)
    raise
```

### 5. テスト

#### テストカバレッジ
- [ ] 新機能にテストが追加されているか
- [ ] エッジケースのテストがあるか
- [ ] 既存のテストが全てパスするか

#### テストの品質
- [ ] テスト名が説明的か（`test_parse_internal_fragment_link`）
- [ ] Arrange-Act-Assert パターンに従っているか
- [ ] アサーションが適切か

```python
# ✅ Good
def test_parse_internal_fragment_link() -> None:
    """Test internal link with fragment parsing."""
    # Arrange
    project_name = "myproject"
    line = "[PageTitle#section]"
    
    # Act
    parsed = ScrapboxParser.parse_line(line, project_name)
    
    # Assert
    assert parsed.line_type == LineType.URL
    assert parsed.content == "https://scrapbox.io/myproject/PageTitle#section"
```

### 6. ドキュメント

#### specification.md の更新
- [ ] 新機能が specification.md に記載されているか
- [ ] 変換ルールの表が更新されているか
- [ ] 実装方針・制限事項が説明されているか

#### README.md の更新（必要に応じて）
- [ ] 使用方法が更新されているか
- [ ] 新しいオプション・フラグが説明されているか

#### コメント
- [ ] 複雑なロジックにコメントがあるか
- [ ] なぜその実装をしたのか（Why）が説明されているか
- [ ] TODO コメントが残っていないか

```python
# ✅ Good
# Don't match if it ends with .icon (that should be handled by ICON_PATTERN)
if not page.endswith(".icon"):
    url = f"https://scrapbox.io/{project}/{page}"

# ❌ Bad
# check icon  # 何をチェックしているのか不明瞭
```

### 7. パフォーマンス

#### 正規表現の効率
- [ ] 正規表現が効率的か（バックトラックが少ないか）
- [ ] パターンがコンパイル済みか（`re.compile()`）

#### 不要な処理の削除
- [ ] 同じ処理が重複していないか
- [ ] 不要な変数・関数が残っていないか

### 8. セキュリティ

#### 入力検証
- [ ] ユーザー入力が適切にサニタイズされているか
- [ ] ファイルパスのトラバーサルが防がれているか（`_sanitize_filename()`）
- [ ] URL の検証が行われているか

#### 認証情報
- [ ] 認証情報がハードコードされていないか
- [ ] 環境変数から読み込まれているか
- [ ] ログに認証情報が出力されていないか

## レビュー時のコメント例

### 良いコメント例

```markdown
**設計について:**
specification.md によると、リストのネストは2階層までという制限があります。
この実装では3階層目まで許可しているようですが、意図的な変更でしょうか？

**テストについて:**
エッジケースとして、以下のテストを追加することを推奨します:
- 空文字列の場合
- 日本語を含む場合
- 特殊文字（#, /, [, ]）を含む場合

**パフォーマンスについて:**
この正規表現は毎回コンパイルされています。
クラス変数として `re.compile()` で事前コンパイルすることを推奨します。
```

### 避けるべきコメント例

```markdown
# ❌ Bad
これは間違っています。

# ❌ Bad  
なぜこのような実装にしたのですか？

# ❌ Bad
もっと良い方法があります。
```

## 承認基準

すべてのチェックリスト項目が満たされ、以下の条件を満たす場合に承認:

1. ✅ specification.md との整合性が確認できている
2. ✅ 全テストがパス（既存+新規）
3. ✅ 型ヒントが適切に使用されている
4. ✅ ドキュメントが更新されている
5. ✅ パフォーマンス・セキュリティ上の問題がない

## 軽微な修正の判断

以下は承認後にも修正可能（別 PR で対応可）:

- typo の修正
- コメントの改善
- 変数名のリネーム（機能に影響しない範囲）
- ログメッセージの改善

以下は承認前に必ず修正が必要:

- テストの失敗
- specification.md との不整合
- 型エラー
- セキュリティ上の問題

## レビュー後のアクション

### マージ前
1. 全テストがパスしていることを再確認
2. specification.md が最新であることを確認
3. 不要なデバッグコード・コメントを削除

### マージ後
1. 関連する Issue をクローズ
2. リリースノートに記載（必要に応じて）
3. 次の作業へ

## トラブルシューティング

### レビュー時によくある問題

**問題**: テストが失敗する
- 原因: 既存の動作を変更してしまった
- 対処: specification.md を確認し、意図的な変更か判断

**問題**: 型エラーが出る
- 原因: 型ヒントが不正確
- 対処: ty の警告を確認

**問題**: specification.md が更新されていない
- 原因: 実装だけして文書化を忘れた
- 対処: 実装内容を specification.md に追記

## 参考資料

- [Python 型ヒントガイド](https://docs.python.org/ja/3/library/typing.html)
- [Google Python スタイルガイド](https://google.github.io/styleguide/pyguide.html)
- [Conventional Comments](https://conventionalcomments.org/)
