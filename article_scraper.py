#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Business Lawyers サイトの新着特集記事を取得して要約し、PDFを生成するスクリプト
"""

import requests
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import datetime
import os
import json

class ArticleScraper:
    def __init__(self):
        self.base_url = "https://www.businesslawyers.jp"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Referer': 'https://www.businesslawyers.jp/'
        }
        self.output_dir = "articles"
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_special_articles(self):
        """特集記事一覧を取得"""
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            articles = []

            # 特集記事のセクションを探す（サイトの構造に応じて調整が必要）
            # 複数のパターンを試す
            special_sections = soup.find_all(['div', 'section'], class_=lambda x: x and ('special' in x.lower() or 'feature' in x.lower()))

            if not special_sections:
                # h2やh3で「特集」を含むセクションを探す
                headings = soup.find_all(['h2', 'h3'], string=lambda x: x and '特集' in x)
                for heading in headings:
                    parent = heading.find_parent(['div', 'section'])
                    if parent:
                        special_sections.append(parent)

            # 記事リンクを抽出
            for section in special_sections[:3]:  # 最初の3つのセクションをチェック
                links = section.find_all('a', href=True)
                for link in links[:5]:  # 各セクションから最大5記事
                    title = link.get_text(strip=True)
                    url = link['href']

                    if not url.startswith('http'):
                        url = self.base_url + url

                    if title and len(title) > 10:  # 意味のあるタイトルのみ
                        articles.append({
                            'title': title,
                            'url': url,
                            'fetched_date': datetime.now().strftime('%Y-%m-%d %H:%M')
                        })

            # 重複を削除
            seen_urls = set()
            unique_articles = []
            for article in articles:
                if article['url'] not in seen_urls:
                    seen_urls.add(article['url'])
                    unique_articles.append(article)

            return unique_articles[:10]  # 最大10記事

        except Exception as e:
            print(f"記事一覧の取得中にエラーが発生: {e}")
            return []

    def fetch_article_content(self, url):
        """記事の本文を取得"""
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # 本文を探す（複数のパターンを試す）
            content = None

            # article タグ
            article_tag = soup.find('article')
            if article_tag:
                content = article_tag

            # main タグ
            if not content:
                main_tag = soup.find('main')
                if main_tag:
                    content = main_tag

            # class に content, article, body などを含む div
            if not content:
                content = soup.find(['div', 'section'], class_=lambda x: x and any(
                    keyword in x.lower() for keyword in ['content', 'article', 'body', 'post']
                ))

            if content:
                # 不要な要素を削除
                for element in content.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()

                # テキストを取得
                paragraphs = content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li'])
                text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

                return text[:2000]  # 最初の2000文字を取得

            return "本文を取得できませんでした。"

        except Exception as e:
            print(f"記事内容の取得中にエラーが発生 ({url}): {e}")
            return f"エラー: {str(e)}"

    def summarize_content(self, content):
        """コンテンツを要約（シンプルな実装）"""
        # 最初の500文字と主要な段落を抽出
        lines = content.split('\n\n')
        summary_parts = []
        total_length = 0

        for line in lines:
            if total_length + len(line) > 800:
                break
            if len(line) > 20:  # 意味のある段落のみ
                summary_parts.append(line)
                total_length += len(line)

        summary = '\n\n'.join(summary_parts)
        if len(summary) > 800:
            summary = summary[:800] + "..."

        return summary if summary else content[:500] + "..."

    def generate_pdf(self, articles_data, filename=None):
        """PDFを生成"""
        if not filename:
            filename = f"{self.output_dir}/business_lawyers_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        doc = SimpleDocTemplate(filename, pagesize=A4,
                                rightMargin=20*mm, leftMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)

        # 日本語フォントの設定（Noto Sans JPを使用する想定）
        # GitHub Actionsで実行する場合は、フォントファイルをリポジトリに含めるか、
        # システムフォントを使用する
        try:
            # DejaVu（多言語対応）を使用
            pdfmetrics.registerFont(TTFont('Japanese', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            font_name = 'Japanese'
        except:
            # フォントが見つからない場合はHelveticaを使用
            font_name = 'Helvetica'
            print("警告: 日本語フォントが見つかりません。Helveticaを使用します。")

        styles = getSampleStyleSheet()

        # カスタムスタイルを作成
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=font_name,
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=12
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=font_name,
            fontSize=12,
            spaceAfter=6
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=9,
            leading=14
        )

        story = []

        # タイトルページ
        title = Paragraph("Business Lawyers 新着特集記事", title_style)
        story.append(title)
        story.append(Spacer(1, 12))

        date_text = Paragraph(f"取得日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}", normal_style)
        story.append(date_text)
        story.append(Spacer(1, 20))

        # 各記事を追加
        for i, article in enumerate(articles_data, 1):
            # 記事タイトル
            article_title = Paragraph(f"{i}. {article['title']}", heading_style)
            story.append(article_title)
            story.append(Spacer(1, 6))

            # URL
            url_text = Paragraph(f"URL: {article['url']}", normal_style)
            story.append(url_text)
            story.append(Spacer(1, 6))

            # 要約
            if 'summary' in article and article['summary']:
                summary_text = Paragraph(f"<b>要約:</b><br/>{article['summary']}", normal_style)
                story.append(summary_text)

            story.append(Spacer(1, 20))

            # 3記事ごとに改ページ
            if i % 3 == 0 and i < len(articles_data):
                story.append(PageBreak())

        # PDFを構築
        doc.build(story)
        print(f"PDFを生成しました: {filename}")
        return filename

    def run(self):
        """メイン処理"""
        print("Business Lawyers から新着特集記事を取得中...")
        articles = self.fetch_special_articles()

        if not articles:
            print("記事が見つかりませんでした。")
            return None

        print(f"{len(articles)}件の記事を取得しました。")

        # 各記事の内容を取得して要約
        for i, article in enumerate(articles, 1):
            print(f"記事 {i}/{len(articles)} を処理中: {article['title']}")
            content = self.fetch_article_content(article['url'])
            article['summary'] = self.summarize_content(content)

        # PDFを生成
        pdf_file = self.generate_pdf(articles)

        # JSON形式でも保存（デバッグ用）
        json_file = f"{self.output_dir}/articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        print(f"JSONファイルも保存しました: {json_file}")

        return pdf_file

if __name__ == "__main__":
    scraper = ArticleScraper()
    scraper.run()
