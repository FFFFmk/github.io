#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記事取得結果をメールで送信するスクリプト
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
import os
import json
import glob

def send_notification_email(recipient_email, smtp_server, smtp_port, smtp_user, smtp_password):
    """
    新着記事の通知メールを送信

    Args:
        recipient_email: 送信先メールアドレス
        smtp_server: SMTPサーバーアドレス
        smtp_port: SMTPポート番号
        smtp_user: SMTP認証ユーザー名
        smtp_password: SMTP認証パスワード
    """

    # 最新のJSONファイルを取得
    json_files = glob.glob("articles/articles_*.json")
    if not json_files:
        print("記事データが見つかりません。")
        return False

    latest_json = max(json_files, key=os.path.getctime)

    # 記事データを読み込む
    with open(latest_json, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    if not articles:
        print("記事がありません。")
        return False

    # メール本文を作成
    email_body = f"""Business Lawyers 新着特集記事のお知らせ

取得日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
記事件数: {len(articles)}件

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    for i, article in enumerate(articles, 1):
        email_body += f"""【記事 {i}】
タイトル: {article['title']}
URL: {article['url']}

要約:
{article.get('summary', '要約なし')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    email_body += f"""
詳細はPDFファイルをご確認ください。

※このメールは自動送信されています。
"""

    # メールメッセージを作成
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = recipient_email
    msg['Subject'] = f"Business Lawyers 新着特集記事 ({len(articles)}件) - {datetime.now().strftime('%Y/%m/%d')}"

    # 本文を追加
    msg.attach(MIMEText(email_body, 'plain', 'utf-8'))

    # PDFファイルを添付
    pdf_files = glob.glob("articles/business_lawyers_articles_*.pdf")
    if pdf_files:
        latest_pdf = max(pdf_files, key=os.path.getctime)
        with open(latest_pdf, 'rb') as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
            pdf_attachment.add_header('Content-Disposition', 'attachment',
                                     filename=os.path.basename(latest_pdf))
            msg.attach(pdf_attachment)

    # メール送信
    try:
        print(f"SMTPサーバー {smtp_server}:{smtp_port} に接続中...")

        if smtp_port == 587:
            # TLS接続
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            server.starttls()
        elif smtp_port == 465:
            # SSL接続
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        else:
            # 通常接続
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)

        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()

        print(f"メールを送信しました: {recipient_email}")
        return True

    except Exception as e:
        print(f"メール送信エラー: {e}")
        return False

if __name__ == "__main__":
    import sys

    # 環境変数から設定を取得
    recipient = os.environ.get('EMAIL_TO', 'fi.13-51@outlook.jp')
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')

    if not smtp_user or not smtp_password:
        print("エラー: SMTP_USER と SMTP_PASSWORD の環境変数を設定してください。")
        sys.exit(1)

    success = send_notification_email(
        recipient_email=recipient,
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password
    )

    sys.exit(0 if success else 1)
