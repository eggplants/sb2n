# sb2n 仕様書

## 概要

sb2nは、Scrapboxの全ページを指定したNotionデータベースへ移行するためのツールです。

## 目的

Scrapboxから機械的にページをコピーし、ラベルを作り、適宜他のデータベースなどに移行するための基盤ツールを提供します。

## 主な機能

### 1. Scrapboxからのページ取得

- Scrapbox APIを使用して、指定したプロジェクトの全ページを取得
- ページのメタデータ（タイトル、作成日、更新日、タグなど）を収集
- ページ本文の取得

### 2. Notionデータベースへの移行

#### 対象データベース構造

Notionの移行先データベースは**フルページデータベース（Full Page Database）**として作成し、以下のプロパティを持つ：

| プロパティ名 | タイプ | 必須 | 説明 |
| ------------ | -------- | ------ | ------ |
| Title | Title | ✓ | ページタイトル（Scrapboxのページ名） |
| Scrapbox URL | URL | ✓ | 元のScrapboxページへのリンク |
| Created Date | Date | ✓ | Scrapboxでのページ作成日時 |
| Tags | Multi-select | | Scrapboxページに含まれるタグ |

##### データベース作成手順

1. **Notionでフルページデータベースを作成**
   - Notionで新規ページを作成
   - `/database` と入力して「データベース - フルページ」を選択
   - または、既存ページで `/table` と入力して「テーブルビュー - フルページ」を選択後、右上の「...」から「データベースに変換」

2. **プロパティを追加・設定**
   - デフォルトの「Name」プロパティを「Title」に変更（またはそのまま「Name」でも可）
   - 「+」ボタンをクリックして以下のプロパティを追加：
     - **Scrapbox URL**: タイプを「URL」に設定
     - **Created Date**: タイプを「日付」に設定
     - **Tags**: タイプを「マルチセレクト」に設定

3. **インテグレーションとの共有**
   - データベースページの右上「...」メニューから「接続を追加」
   - 作成したインテグレーションを選択して共有

4. **データベースIDの取得**
   - データベースのURLから32文字のIDをコピー
   - 例: `https://www.notion.so/{workspace}/{database_id}?v=...`
   - `database_id` 部分（ハイフンなし32文字）を `.env` の `NOTION_DATABASE_ID` に設定

#### 移行データ

- **タイトル**: Scrapboxのページタイトルをそのまま使用
- **Scrapbox URL**: `https://scrapbox.io/{project}/{page_title}` 形式
- **作成日**: Scrapboxページの作成日時（Unix timestamp から変換）
- **タグ**: Scrapboxページ内のハッシュタグ（`#tag` 形式）を抽出してMulti-selectとして設定
- **本文**: Notionページの本文として、Scrapbox記法からNotion Blocksへ変換して格納

### 3. 画像の移行

- Scrapboxページに含まれる画像（`[image_url]` 形式）を検出
- 画像がScrapbox上にホストされている場合（`https://gyazo.com/` など）は、画像をダウンロード
- ダウンロードした画像をNotionへアップロード
- Notion Block内で画像を適切に配置

### 4. 認証情報の管理

`.env` ファイルから以下の認証情報を読み込む：

```env
# Scrapbox API設定
SCRAPBOX_PROJECT=your-project-name
SCRAPBOX_COOKIE_CONNECT_SID=your-connect-sid

# Notion API設定
NOTION_API_KEY=secret_xxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxx
```

#### 認証情報の説明

- **SCRAPBOX_PROJECT**: 移行元のScrapboxプロジェクト名
- **SCRAPBOX_COOKIE_CONNECT_SID**: Scrapbox APIアクセス用のCookie（プライベートプロジェクトの場合に必要）
- **NOTION_API_KEY**: Notion Integration Token
- **NOTION_DATABASE_ID**: 移行先のNotionデータベースID

## 技術仕様

### 使用言語・ライブラリ

#### Python

- **バージョン**: Python >= 3.14

#### 主要ライブラリ

##### scrapbox-client

Scrapbox APIとのやり取りを行うためのPythonクライアントライブラリ。

- **PyPI**: [scrapbox-client](https://pypi.org/project/scrapbox-client/)
- **ドキュメント**: <https://egpl.dev/scrapbox-client/scrapbox.html>
- **バージョン**: >= 0.1.0

**主な機能:**

- `ScrapboxClient`: Scrapbox APIクライアント
  - `get_pages(project_name, skip, limit)`: ページ一覧取得
  - `get_page(project_name, page_title)`: ページ詳細取得
  - `get_page_text(project_name, page_title)`: ページテキスト取得
  - `get_page_icon_url(project_name, page_title)`: ページアイコンURL取得
  - `get_file(file_id)`: ファイル（画像など）のダウンロード
- 認証: `connect_sid` Cookie による認証（プライベートプロジェクト用）
- レスポンスモデル: `PageListResponse`, `PageDetail`, `PageListItem`, `Line`

**使用例:**

```python
from scrapbox.client import ScrapboxClient

# 認証情報付きでクライアント初期化
with ScrapboxClient(connect_sid="s%3AykQ__xxxxx-...") as client:
    # 全ページリストを取得
    pages = client.get_pages("project-name", skip=0, limit=100)
    
    # 個別ページの詳細取得
    page_detail = client.get_page("project-name", "Page Title")
    
    # 画像ファイルのダウンロード
    image_data = client.get_file("1a2b3c4d5e6f7g8h9i0j.JPG")
```

##### notion-client

Notion APIとのやり取りを行うためのPythonクライアントライブラリ。

- **PyPI**: [notion-client](https://pypi.org/project/notion-client/)
- **ドキュメント**: <https://ramnes.github.io/notion-sdk-py/>
- **バージョン**: >= 2.7.0

**主な機能:**

- `Client` / `AsyncClient`: Notion APIクライアント（同期/非同期）
- APIエンドポイントへのアクセス:
  - `pages.create()`: ページ作成
  - `blocks.children.append()`: ブロック追加
  - `data_sources.query()`: データベースクエリ
- ヘルパー関数:
  - `iterate_paginated_api()`: ページネーションAPIのイテレータ
  - `collect_paginated_api()`: ページネーションAPIの一括取得
  - `is_full_page()`, `is_full_block()`: レスポンス型判定
- エラーハンドリング: `APIResponseError`, `APIErrorCode`
- ログ設定可能

**使用例:**

```python
import os
from notion_client import Client

# クライアント初期化
notion = Client(auth=os.environ["NOTION_TOKEN"])

# データベースにページを作成
new_page = notion.pages.create(
    parent={"database_id": database_id},
    properties={
        "Name": {"title": [{"text": {"content": "Page Title"}}]},
        "URL": {"url": "https://scrapbox.io/project/page"},
    },
)

# ページにブロックを追加
notion.blocks.children.append(
    block_id=new_page["id"],
    children=[
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "Hello, world!"}}]
            },
        }
    ],
)
```

##### その他のライブラリ

- **python-dotenv**: `.env` ファイルからの環境変数読み込み
- **httpx**: HTTP通信（scrapbox-client/notion-clientが内部使用）

### 使用API

#### Scrapbox API

- **ベースURL**: `https://scrapbox.io/api`
- **ページ一覧取得**: `GET /pages/{project}`
- **ページ詳細取得**: `GET /pages/{project}/{title}`
- **ファイル取得**: `GET /files/{file_id}`

#### Notion API

- **ベースURL**: `https://api.notion.com/v1`
- **データベースページ作成**: `POST /pages`
- **ブロック追加**: `POST /blocks/{block_id}/children`
- **画像アップロード**: external または file タイプを使用

### データ変換ロジック

#### Scrapbox記法 → Notion Blocks 変換

##### 現在実装されている記法

| Scrapbox記法 | Notion Block Type | 実装状態 |
|-------------|------------------|---------|
| 通常テキスト | paragraph | ✅ |
| `[* 見出し]` | heading_2 | ✅ |
| `[** 見出し2]` | heading_3 | ✅ |
| `[*** 見出し3]` | heading_3 | ✅ |
| `[https://example.com]` | bookmark or link | ✅ |
| `[image_url]` | image | ✅ |
| `` `code` `` | code (inline) | 部分的 |
| `code:filename` ブロック | code block | ✅ |
| 箇条書き（インデント） | bulleted_list_item | ✅ |
| `[link text]` | 内部リンク（通常テキストとして扱う） | ✅ |
| `#tag` | タグとして抽出（Multi-selectへ） | ✅ |

##### Scrapbox記法の完全なリスト（公式Syntax参照）

###### テキスト装飾

| Scrapbox記法 | 説明 | 実装状態 | 優先度 |
|-------------|-----|---------|-------|
| `[[文字列]]` | 太字（bold） | ❌ | 高 |
| `[* 文字列]` | 斜体（italic） | ❌ | 高 |
| `[- 文字列]` | 取り消し線（strikethrough） | ❌ | 中 |
| `[_ 文字列]` | 下線（underline） | ❌ | 中 |
| `` `code` `` | インラインコード | 部分的 | 高 |
| `[/ 文字列]` | 数式（KaTeX） | ❌ | 低 |
| `[$ 数式]` | 数式ブロック（KaTeX） | ❌ | 低 |

注: Scrapboxでは `[* 見出し]` が見出しで、`[* 文字列]` が斜体だが、文脈によって判別される。見出しは行全体が `[*...]` の形式。

###### リンク

| Scrapbox記法 | 説明 | 実装状態 | 優先度 |
|-------------|-----|---------|-------|
| `[リンクテキスト]` | 内部リンク | ✅（テキスト化） | - |
| `[リンクテキスト URL]` | 外部リンク（表示テキスト付き） | ❌ | 高 |
| `[URL リンクテキスト]` | 外部リンク（表示テキスト付き・逆順） | ❌ | 高 |
| `http://example.com` | URL自動リンク | 部分的 | 中 |
| `#ハッシュタグ` | ハッシュタグ（内部リンク） | ✅（タグ抽出） | - |

###### メディア

| Scrapbox記法 | 説明 | 実装状態 | 優先度 |
|-------------|-----|---------|-------|
| `[image_url]` | 画像埋め込み | ✅ | - |
| `[youtube_url]` | YouTube埋め込み | ❌ | 対応不要 |
| `[vimeo_url]` | Vimeo埋め込み | ❌ | 対応不要 |
| `[spotify_url]` | Spotify埋め込み | ❌ | 対応不要 |
| `[soundcloud_url]` | SoundCloud埋め込み | ❌ | 対応不要 |
| `[twitter_url]` | Twitter埋め込み | ❌ | 対応不要 |

###### 構造

| Scrapbox記法 | 説明 | 実装状態 | 優先度 |
|-------------|-----|---------|-------|
| `[* 見出し]` | 見出しレベル2 | ✅ | - |
| `[** 見出し]` | 見出しレベル3 | ✅ | - |
| `[*** 見出し]` | 見出しレベル3（Notionは3まで） | ✅ | - |
| スペースによるインデント | 箇条書き | ✅ | - |
| `code:filename` | コードブロック | ✅ | - |
| `table:テーブル名` | テーブル記法 | ❌ | 中 |

###### アイコン

| Scrapbox記法 | 説明 | 実装状態 | 優先度 |
|-------------|-----|---------|-------|
| `[icon_name.icon]` | Scrapboxアイコン | ❌ | 低 |
| `[/icons/icon_name.icon]` | Notion風アイコン | ❌ | 低 |

###### 引用・吹き出し

| Scrapbox記法 | 説明 | 実装状態 | 優先度 |
|-------------|-----|---------|-------|
| `> 引用文` | 引用（quote） | ❌ | 中 |

###### その他

| Scrapbox記法 | 説明 | 実装状態 | 優先度 |
|-------------|-----|---------|-------|
| 空行 | パラグラフ区切り | ✅ | - |
| `---` | 水平線 | ❌ | 低 |

##### 実装の注意事項

1. **テキスト装飾の入れ子**: Scrapboxでは `[[*文字列]]` のような入れ子が可能だが、Notionでも同様に対応する必要がある
2. **内部リンク**: Scrapboxの内部リンクは移行後のNotionでは同名ページへのリンクに変換可能（データベース内検索が必要）
3. **リッチテキスト**: Notion APIでは `rich_text` 配列で複数のスタイルを表現可能
4. **テーブル**: Notion APIでは `table` ブロックがあるが、複雑な構造のため対応は慎重に
5. **数式**: Notionでも `equation` ブロックで対応可能

##### 優先実装すべき記法

1. **太字・斜体・取り消し線などのテキスト装飾**: 最も頻繁に使われる
2. **外部リンク（表示テキスト付き）**: `[Google https://google.com]` 形式
3. **引用ブロック**: 一般的な記法
4. **テーブル記法**: データ整理に有用

##### 対応不要の記法

- **メディア埋め込み**: YouTube、Vimeo、Spotify、SoundCloud、Twitter等の外部サービス埋め込みは対応しない
- これらのURLは通常のbookmarkまたはリンクとして扱う

### エラーハンドリング

- APIレート制限への対応（リトライロジック）
- ページ移行失敗時のログ記録
- 部分的な移行失敗時の続行可否判断
- 画像ダウンロード失敗時の代替処理

### ログ出力

- 移行進捗状況の表示
- エラー・警告のログ記録
- 移行完了後のサマリー表示

## 実行フロー

```text
1. 環境変数の読み込み（.env）
   ↓
2. Scrapbox APIから全ページリストを取得
   ↓
3. 各ページに対して以下を実行：
   a. ページ詳細を取得
   b. タグを抽出
   c. 画像URLを検出・ダウンロード
   d. Scrapbox記法をNotion Blocks形式に変換
   e. Notionデータベースにページを作成
   f. 画像をアップロード
   g. ブロックをNotionページに追加
   ↓
4. 移行結果のサマリーを表示
```

## コマンドラインインターフェース

```bash
# 基本的な実行
sb2n migrate

# .envファイルを指定
sb2n migrate --env-file /path/to/.env

# ドライラン（実際には移行しない）
sb2n migrate --dry-run

# 特定のページのみ移行
sb2n migrate --pages "ページ1,ページ2"

# 既存ページをスキップ
sb2n migrate --skip-existing
```

## 制約事項

1. Scrapboxの全ての記法がNotionで完全に再現できるわけではない
2. Scrapboxの内部リンク構造はNotionでは単純なテキストとして扱う
3. 大量のページを移行する場合、API制限により時間がかかる可能性がある
4. Gyazo以外の外部画像サービスについては対応が限定的な場合がある

## 今後の拡張可能性

- 双方向同期機能
- 段階的な移行（バッチ処理）
- カスタムマッピング設定（プロパティのカスタマイズ）
- Scrapboxのバックリンク情報の保持

## 参考リンク

- [Scrapbox API Documentation](https://scrapbox.io/help-jp/API)
- [Notion API Documentation](https://developers.notion.com/)
