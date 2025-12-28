"""
Email notification sender for classified ads.
"""

from typing import Dict, List
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailSender:
    """Send email notifications for new ads."""

    def __init__(self, config: Dict):
        """
        Initialize email sender.

        Args:
            config: Email configuration
        """
        self.config = config
        self.smtp_config = config.get("smtp", {})
        self.from_email = config.get("from_email", "noreply@example.com")
        self.from_name = config.get("from_name", "Classified Ads Notifier")

    def send_email(self, to: str, subject: str, html_content: str) -> bool:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML email content

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to
            msg['Date'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # Send via SMTP
            with smtplib.SMTP(
                self.smtp_config.get("host", "localhost"),
                self.smtp_config.get("port", 587)
            ) as server:
                if self.smtp_config.get("use_tls", True):
                    server.starttls()

                if self.smtp_config.get("username") and self.smtp_config.get("password"):
                    server.login(
                        self.smtp_config["username"],
                        self.smtp_config["password"]
                    )

                server.send_message(msg)

            logger.info(f"Email sent to {to}")
            return True

        except Exception as e:
            logger.error(f"Error sending email to {to}: {e}")
            return False

    def send_ad_digest(self, to: str, ads: List[Dict], filters: Dict = None) -> bool:
        """
        Send a digest of ads to a user.

        Args:
            to: Recipient email address
            ads: List of ad dictionaries
            filters: User's filter settings (optional)

        Returns:
            True if sent successfully
        """
        if not ads:
            logger.info(f"No ads to send to {to}")
            return False

        # Generate email content
        subject = f"Neue kostenlose Anzeigen ({len(ads)})"
        html_content = self._generate_digest_html(ads, filters)

        return self.send_email(to, subject, html_content)

    def _generate_digest_html(self, ads: List[Dict], filters: Dict = None) -> str:
        """
        Generate HTML content for ad digest.

        Args:
            ads: List of ads
            filters: User filters (optional)

        Returns:
            HTML string
        """
        # HTML template
        html_parts = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '<meta charset="utf-8">',
            '<style>',
            '  body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }',
            '  h1 { color: #333; }',
            '  .ad-item { border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px; }',
            '  .ad-title { font-size: 18px; font-weight: bold; color: #0066cc; margin-bottom: 10px; }',
            '  .ad-location { color: #666; font-size: 14px; }',
            '  .ad-category { display: inline-block; background: #f0f0f0; padding: 5px 10px; ',
            '                 border-radius: 3px; font-size: 12px; margin: 5px 0; }',
            '  .ad-description { margin: 10px 0; }',
            '  .ad-link { display: inline-block; background: #0066cc; color: white; padding: 8px 15px; ',
            '             text-decoration: none; border-radius: 3px; margin-top: 10px; }',
            '  .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; ',
            '            color: #666; font-size: 12px; }',
            '</style>',
            '</head>',
            '<body>',
        ]

        # Header
        html_parts.append('<h1>Neue kostenlose Anzeigen</h1>')
        html_parts.append(f'<p>Hallo! Wir haben <strong>{len(ads)}</strong> neue Anzeigen für Sie gefunden.</p>')

        # Show filters if provided
        if filters:
            filter_parts = []
            if filters.get("categories"):
                filter_parts.append(f"Kategorien: {', '.join(filters['categories'])}")
            if filters.get("city"):
                filter_parts.append(f"Stadt: {filters['city']}")
            if filter_parts:
                html_parts.append(f'<p style="color: #666;"><em>Filter: {" | ".join(filter_parts)}</em></p>')

        # Ad items
        for ad in ads:
            html_parts.append('<div class="ad-item">')

            # Title
            title = ad.get("title", "Kein Titel")
            html_parts.append(f'<div class="ad-title">{title}</div>')

            # Category
            if ad.get("category"):
                html_parts.append(f'<span class="ad-category">{ad["category"]}</span>')

            # Location
            location = ad.get("location", {})
            if isinstance(location, dict):
                location_str = ", ".join(filter(None, [
                    location.get("city"),
                    location.get("district")
                ]))
            else:
                location_str = str(location)

            if location_str:
                html_parts.append(f'<div class="ad-location">📍 {location_str}</div>')

            # Description (truncated)
            description = ad.get("description", "")
            if len(description) > 200:
                description = description[:200] + "..."
            html_parts.append(f'<div class="ad-description">{description}</div>')

            # Features
            if ad.get("features"):
                features = ad["features"]
                if isinstance(features, dict):
                    feature_parts = []
                    if features.get("condition"):
                        feature_parts.append(f"Zustand: {features['condition']}")
                    if features.get("brand"):
                        feature_parts.append(f"Marke: {features['brand']}")
                    if feature_parts:
                        html_parts.append(f'<div style="font-size: 13px; color: #666;">{" | ".join(feature_parts)}</div>')

            # Link
            url = ad.get("url", "#")
            html_parts.append(f'<a href="{url}" class="ad-link">Anzeige ansehen</a>')

            html_parts.append('</div>')

        # Footer
        html_parts.append('<div class="footer">')
        html_parts.append('<p>Diese E-Mail wurde automatisch generiert.</p>')
        html_parts.append('<p>Um Ihre Benachrichtigungen zu ändern oder abzubestellen, besuchen Sie bitte Ihre Einstellungen.</p>')
        html_parts.append('</div>')

        html_parts.append('</body>')
        html_parts.append('</html>')

        return '\n'.join(html_parts)

    def test_connection(self) -> bool:
        """
        Test SMTP connection.

        Returns:
            True if connection successful
        """
        try:
            with smtplib.SMTP(
                self.smtp_config.get("host", "localhost"),
                self.smtp_config.get("port", 587),
                timeout=10
            ) as server:
                if self.smtp_config.get("use_tls", True):
                    server.starttls()

                if self.smtp_config.get("username") and self.smtp_config.get("password"):
                    server.login(
                        self.smtp_config["username"],
                        self.smtp_config["password"]
                    )

            logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
