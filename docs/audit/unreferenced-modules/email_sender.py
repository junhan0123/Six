#!/usr/bin/env python3
"""Email notification utility for Xiao6"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
QQ_EMAIL = "1903999022@qq.com"
QQ_AUTH_CODE = "vqmlyrdnrycibiab"


def send_email(subject, body, recipients=None):
    """发送邮件通知"""
    if recipients is None:
        recipients = [QQ_EMAIL]
    
    msg = MIMEMultipart()
    msg["From"] = QQ_EMAIL
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    
    msg.attach(MIMEText(body, "plain", "utf-8"))
    
    try:
        # 尝试多种方式
        for port, use_ssl in [(587, False), (465, True), (25, False)]:
            try:
                if use_ssl:
                    server = smtplib.SMTP_SSL(SMTP_SERVER, port, timeout=10)
                else:
                    server = smtplib.SMTP(SMTP_SERVER, port, timeout=10)
                    if port == 587:
                        server.starttls()
                server.login(QQ_EMAIL, QQ_AUTH_CODE)
                server.sendmail(QQ_EMAIL, recipients, msg.as_string())
                server.quit()
                print(f"✓ 邮件发送成功 (port={port}, ssl={use_ssl}): {subject}")
                return True
            except Exception as e:
                print(f"  尝试 port={port} ssl={use_ssl} 失败: {e}")
                continue
        return False
    except Exception as e:
        print(f"✗ 邮件发送失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    send_email(
        "Xiao6 v1.0.0 - PHASE 132 测试",
        "这是一封测试邮件，验证 QQ 邮箱配置。"
    )