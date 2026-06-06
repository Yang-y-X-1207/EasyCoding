"""
Notification Service
Phase 8: Code review notifications via Slack and Email
"""
import httpx
import smtplib
import logging
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    """Result of notification sending"""
    success: bool
    channel: str
    message: str


class NotificationService:
    """
    Service for sending code review notifications via Slack and Email.
    """

    def __init__(self):
        self.slack_token = ""
        self.slack_channel = ""
        self.smtp_server = ""
        self.smtp_port = 587
        self.smtp_user = ""
        self.smtp_password = ""
        self.email_from = ""

    def configure_slack(self, token: str, default_channel: str = "") -> None:
        """Configure Slack notification"""
        self.slack_token = token
        self.slack_channel = default_channel

    def configure_email(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_addr: str,
    ) -> None:
        """Configure Email notification"""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_from = from_addr

    async def notify_review_slack(
        self,
        pr_url: str,
        pr_number: int,
        title: str,
        author: str,
        reviewers: list[str],
        changed_files: list[str],
        channel: Optional[str] = None,
    ) -> NotificationResult:
        """
        Send code review notification to Slack.

        Args:
            pr_url: PR/MR URL
            pr_number: PR/MR number
            title: PR title
            author: PR author
            reviewers: List of reviewer mentions
            changed_files: List of changed files
            channel: Slack channel (uses default if not specified)

        Returns:
            NotificationResult with success status
        """
        if not self.slack_token:
            return NotificationResult(
                success=False,
                channel="slack",
                message="Slack token not configured",
            )

        target_channel = channel or self.slack_channel or "#code-review"

        # Format reviewers mention
        reviewer_mentions = " ".join(f"@{r}" for r in reviewers) if reviewers else ""

        # Format file list
        files_text = "\n".join(f"  • `{f}`" for f in changed_files[:10])
        if len(changed_files) > 10:
            files_text += f"\n  • ... and {len(changed_files) - 10} more files"

        payload = {
            "channel": target_channel,
            "text": f":bell: *代码审核请求*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🔍 代码审核请求",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*PR/MR:*\n<{pr_url}|#{pr_number}>",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*作者:*\n{author}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*标题:*\n{title}",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*变更文件:*\n{files_text}",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "查看代码"},
                            "url": pr_url,
                            "action_id": "view_pr",
                        },
                    ],
                },
            ],
        }

        if reviewer_mentions:
            payload["text"] += f"\n{reviewer_mentions}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.slack_token}",
                        "Content-Type": "application/json",
                    },
                )

                data = response.json()
                if data.get("ok"):
                    return NotificationResult(
                        success=True,
                        channel=target_channel,
                        message="Notification sent successfully",
                    )
                else:
                    return NotificationResult(
                        success=False,
                        channel=target_channel,
                        message=data.get("error", "Unknown error"),
                    )

        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return NotificationResult(
                success=False,
                channel="slack",
                message=str(e),
            )

    def notify_review_email(
        self,
        to_addresses: list[str],
        subject: str,
        pr_url: str,
        pr_number: int,
        title: str,
        author: str,
        changed_files: list[str],
        body_content: str = "",
    ) -> NotificationResult:
        """
        Send code review notification via Email.

        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            pr_url: PR/MR URL
            pr_number: PR/MR number
            title: PR title
            author: PR author
            changed_files: List of changed files
            body_content: Additional body content

        Returns:
            NotificationResult with success status
        """
        if not self.smtp_server or not self.email_from:
            return NotificationResult(
                success=False,
                channel="email",
                message="Email not configured",
            )

        # Format files list
        files_html = "<ul>"
        for f in changed_files[:20]:
            files_html += f"<li><code>{f}</code></li>"
        if len(changed_files) > 20:
            files_html += f"<li>... and {len(changed_files) - 20} more files</li>"
        files_html += "</ul>"

        html_body = f"""
        <html>
        <body>
            <h2>🔍 代码审核请求</h2>

            <table>
                <tr><td><strong>PR/MR:</strong></td><td><a href="{pr_url}">#{pr_number}</a></td></tr>
                <tr><td><strong>标题:</strong></td><td>{title}</td></tr>
                <tr><td><strong>作者:</strong></td><td>{author}</td></tr>
            </table>

            <h3>变更文件</h3>
            {files_html}

            <h3>描述</h3>
            <p>{body_content or '无'}</p>

            <p>
                <a href="{pr_url}">点击查看代码</a>
            </p>

            <hr>
            <p><small>此邮件由 Coding-CLI 自动发送</small></p>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Review] {subject}"
        msg["From"] = self.email_from
        msg["To"] = ", ".join(to_addresses)

        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            return NotificationResult(
                success=True,
                channel="email",
                message=f"Email sent to {len(to_addresses)} recipients",
            )

        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return NotificationResult(
                success=False,
                channel="email",
                message=str(e),
            )

    def notify_status_change(
        self,
        task_id: str,
        status: str,
        message: str,
        channel: str = "slack",
    ) -> NotificationResult:
        """
        Send task status change notification.

        Args:
            task_id: Task identifier
            status: New status
            message: Status message
            channel: Notification channel (slack or email)

        Returns:
            NotificationResult
        """
        status_emoji = {
            "pending_review": "⏳",
            "approved": "✅",
            "rejected": "❌",
            "merged": "🎉",
            "changes_requested": "🔧",
        }

        emoji = status_emoji.get(status, "📋")
        text = f"{emoji} *任务状态更新*\n\n*Task:* {task_id}\n*状态:* {status}\n*消息:* {message}"

        if channel == "slack" and self.slack_token:
            return NotificationService()._send_slack_message(text)
        elif channel == "email" and self.smtp_server:
            return NotificationService()._send_email_simple(
                subject=f"[Task Update] {task_id}",
                body=text,
            )

        return NotificationResult(
            success=False,
            channel=channel,
            message="Channel not configured",
        )

    def _send_slack_message(self, text: str) -> NotificationResult:
        """Send simple Slack message"""
        try:
            import httpx
            import asyncio

            async def send():
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://slack.com/api/chat.postMessage",
                        json={
                            "channel": self.slack_channel,
                            "text": text,
                        },
                        headers={
                            "Authorization": f"Bearer {self.slack_token}",
                            "Content-Type": "application/json",
                        },
                    )

            asyncio.run(send())
            return NotificationResult(success=True, channel="slack", message="Sent")

        except Exception as e:
            return NotificationResult(success=False, channel="slack", message=str(e))

    def _send_email_simple(self, subject: str, body: str) -> NotificationResult:
        """Send simple email"""
        try:
            msg = MIMEText(body, "plain")
            msg["Subject"] = subject
            msg["From"] = self.email_from

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            return NotificationResult(success=True, channel="email", message="Sent")

        except Exception as e:
            return NotificationResult(success=False, channel="email", message=str(e))