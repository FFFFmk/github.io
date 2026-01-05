# ダメ人間のFX奮闘記

FXトレードに関するブログサイトです。

## 記事更新通知機能

このリポジトリには、[Business Lawyers](https://www.businesslawyers.jp) の新着特集記事を自動的に取得し、要約をPDFにまとめる機能が実装されています。

### 機能概要

- **自動実行**: GitHub Actionsにより毎日1回自動実行
- **記事取得**: Business Lawyersの新着特集記事を自動収集
- **要約生成**: 各記事の内容を要約
- **PDF出力**: 見やすいPDF形式で保存
- **メール通知**: 新着記事をメールで自動通知（PDF添付）

### 生成されるファイル

スクリプトの実行により、以下のファイルが `articles/` ディレクトリに生成されます：

- `business_lawyers_articles_YYYYMMDD_HHMMSS.pdf` - 記事の要約PDF
- `articles_YYYYMMDD_HHMMSS.json` - 記事データのJSON形式

### 手動実行方法

#### ローカル環境での実行

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# スクリプトの実行
python article_scraper.py
```

#### GitHub Actionsでの手動実行

1. GitHubリポジトリの「Actions」タブを開く
2. 「Business Lawyers 記事スクレイパー」ワークフローを選択
3. 「Run workflow」ボタンをクリック

### 実行スケジュール

- **自動実行**: 毎日日本時間10時（UTC 1時）
- **手動実行**: いつでも可能

### メール通知の設定

新着記事をメールで受信するには、GitHub Secretsに以下の設定が必要です。

#### 1. GitHub Secretsの設定

リポジトリの `Settings` → `Secrets and variables` → `Actions` で以下のシークレットを追加してください：

| シークレット名 | 説明 | 例 |
|---|---|---|
| `SMTP_SERVER` | SMTPサーバーアドレス | `smtp.gmail.com` |
| `SMTP_PORT` | SMTPポート番号 | `587` (TLS) または `465` (SSL) |
| `SMTP_USER` | SMTP認証ユーザー名（メールアドレス） | `your-email@gmail.com` |
| `SMTP_PASSWORD` | SMTP認証パスワード | アプリパスワード |

#### 2. Gmail を使用する場合

1. Googleアカウントで[2段階認証を有効化](https://myaccount.google.com/security)
2. [アプリパスワードを生成](https://myaccount.google.com/apppasswords)
3. 生成されたパスワードを `SMTP_PASSWORD` に設定

**設定例:**
- `SMTP_SERVER`: `smtp.gmail.com`
- `SMTP_PORT`: `587`
- `SMTP_USER`: `your-email@gmail.com`
- `SMTP_PASSWORD`: 生成されたアプリパスワード（16桁）

#### 3. Outlook.com を使用する場合

**設定例:**
- `SMTP_SERVER`: `smtp-mail.outlook.com`
- `SMTP_PORT`: `587`
- `SMTP_USER`: `your-email@outlook.com`
- `SMTP_PASSWORD`: Outlookアカウントのパスワード

#### 4. 通知先メールアドレス

通知先は `fi.13-51@outlook.jp` に設定されています。

変更する場合は `.github/workflows/article-scraper.yml` の `EMAIL_TO` を編集してください。

#### 5. メール送信のテスト

ローカルでテストする場合：

```bash
export EMAIL_TO="fi.13-51@outlook.jp"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"

python send_email.py
```

### ファイル構成

```
.
├── index.html                    # ブログのメインページ
├── article_scraper.py            # 記事スクレイピングスクリプト
├── send_email.py                 # メール送信スクリプト
├── requirements.txt              # Python依存パッケージ
├── .github/
│   └── workflows/
│       └── article-scraper.yml   # GitHub Actions設定
└── articles/                     # 生成されたPDFとJSONの保存先
```

### 技術スタック

- **Python 3.11**
- **Beautiful Soup 4** - HTMLパース
- **Requests** - HTTPリクエスト
- **ReportLab** - PDF生成
- **GitHub Actions** - 自動実行

### カスタマイズ

`article_scraper.py` を編集することで、以下のカスタマイズが可能です：

- 取得する記事の最大数（現在は10件）
- 要約の長さ（現在は800文字）
- PDF生成のスタイル
- スクレイピング対象のセクション

### 注意事項

- スクレイピングは対象サイトの利用規約を遵守してください
- アクセス頻度が高すぎると、サイトに負荷をかける可能性があります
- サイトの構造変更により、スクリプトの修正が必要になる場合があります

### ライセンス

MIT License
