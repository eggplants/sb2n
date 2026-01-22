# Lark Parser実装状況

## 概要

Scrapbox記法のパーサーをLarkライブラリで実装しました。

- **文法ファイル**: [sb2n/scrapbox.lark](../sb2n/scrapbox.lark)
- **パーサー実装**: [sb2n/lark_parser.py](../sb2n/lark_parser.py)
- **仕様書**: [docs/scrapbox-syntax-spec.md](scrapbox-syntax-spec.md)

## 実装済み機能

### ブロック要素

- ✅ 段落
- ✅ 箇条書き（インデント検出）
- ✅ コードブロックヘッダー (`code:言語名`)
- ✅ テーブルヘッダー (`table:テーブル名`)
- ✅ 引用 (`> テキスト`)
- ✅ コールアウト (`? テキスト`)
- ✅ コマンドライン (`$`, `%`)

### インライン要素

- ✅ ハッシュタグ (`#tag`)
- ✅ インラインコード (`` `code` ``)
- ✅ プレーンテキスト

### ブラケット記法（部分的）

- ⚠️ ページリンク（トークン衝突により未動作）
- ⚠️ 文字装飾（トークン衝突により未動作）
- ⚠️ 外部リンク（トークン衝突により未動作）
- ⚠️ 画像（トークン衝突により未動作）
- ⚠️ アイコン記法（トークン衝突により未動作）
- ⚠️ Location記法（未テスト）
- ⚠️ インライン数式（未テスト）
- ⚠️ クロスプロジェクトリンク（トークン衝突により未動作）

## 現在の課題

### 1. トークン優先順位の問題

Larkのトークナイザーは、最長一致と定義順序に基づいてトークンを決定します。
現在の実装では、`PAGE_NAME` や `ICON_PATH` などのトークンが広すぎるパターンを持っているため、他のパターンと衝突しています。

**例:**

- `[ページリンク]` → `PAGE_NAME` として `ページリンク` を認識するが、`.icon` が続くことを期待してしまう
- `[https://example.com]` → `https:` が `ICON_PATH` として認識され、`//` が `DECO_SYMBOLS` として認識される

### 2. ブラケット内のコンテキスト依存パース

Scrapbox記法では、ブラケット内の内容が何であるかは、内容自体のパターンに依存します:

- URL パターン → 外部リンク
- `.icon` で終わる → アイコン記法
- 装飾記号で始まる → 文字装飾
- その他 → ページリンク

これを実現するには、以下のアプローチが必要です:

#### オプション A: トークナイザーモード

Larkの `@declare` でコンテキストごとに異なるトークナイザーモードを使用する。

#### オプション B: より詳細なトークン定義

より具体的なトークンパターンを定義し、優先順位を明確にする。

#### オプション C: Parser Postprocessing

パーサー後の木構造を解析し、適切な型に変換する。

## 推奨される解決策

### 1. ブラケット内容を文字列として取得

ブラケット内の内容を一旦文字列として取得し、Python側でパースする:

```lark
bracket: "[" BRACKET_CONTENT "]"
BRACKET_CONTENT: /[^\]]+/
```

### 2. Transformer でパース

`ScrapboxTransformer` の `bracket` メソッドで、文字列の内容を解析し、適切な型を判定:

```python
def bracket(self, items):
    content = str(items[0])
    
    # URLパターンチェック
    if content.startswith("http://") or content.startswith("https://"):
        if " " in content:
            return self.parse_link_with_text(content)
        return {"type": "link", "url": content}
    
    # アイコン記法チェック
    if content.endswith(".icon"):
        return self.parse_icon(content)
    
    # 装飾記号チェック
    if content[0] in "*/-_!#%":
        return self.parse_decoration(content)
    
    # デフォルト: ページリンク
    return {"type": "page_link", "page": content}
```

### 3. メリット

- シンプルな文法定義
- 柔軟なパースロジック
- メンテナンスが容易
- 優先順位の制御が簡単

## 次のステップ

1. ✅ Lark文法を簡略化（ブラケット内容を文字列として取得）
2. ⬜ Transformer でブラケット内容を解析
3. ⬜ 各記法のパースロジックを実装
4. ⬜ ユニットテストを作成
5. ⬜ 既存パーサーとの統合

## テスト方法

```bash
# パーサーのテスト実行
uv run python -m sb2n.lark_parser

# 特定のテキストをパース
uv run python -c "from sb2n.lark_parser import ScrapboxLarkParser; \
    p = ScrapboxLarkParser(); \
    print(p.parse('[ページリンク]\n'))"
```

## 参考資料

- [Lark Documentation](https://lark-parser.readthedocs.io/)
- [Scrapbox Syntax Specification](scrapbox-syntax-spec.md)
- [Scrapbox Syntax Reference](scrapbox-syntax-reference.md)
