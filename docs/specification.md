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

| Scrapbox記法 | Notion Block Type |
|-------------|------------------|
| 通常テキスト | paragraph |
| `[* 見出し]` | heading_2 |
| `[** 見出し2]` | heading_3 |
| `[*** 見出し3]` | heading_3 |
| `[https://example.com]` | bookmark or link |
| `[image_url]` | image |
| `` `code` `` | code (inline) |
| `code:filename` ブロック | code block |
| 箇条書き（インデント） | bulleted_list_item |
| `[link text]` | 内部リンク（通常テキストとして扱う） |
| `#tag` | タグとして抽出（Multi-selectへ） |

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
