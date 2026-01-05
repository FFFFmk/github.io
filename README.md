# ダメ人間のFX奮闘記

FXトレードに関するブログサイトです。

## 記事更新通知機能

このリポジトリには、[Business Lawyers](https://www.businesslawyers.jp) の新着特集記事を自動的に取得し、要約をPDFにまとめる機能が実装されています。

### 機能概要

- **自動実行**: GitHub Actionsにより毎日1回自動実行
- **記事取得**: Business Lawyersの新着特集記事を自動収集
- **要約生成**: 各記事の内容を要約
- **PDF出力**: 見やすいPDF形式で保存

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

### ファイル構成

```
.
├── index.html                    # ブログのメインページ
├── article_scraper.py            # 記事スクレイピングスクリプト
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
