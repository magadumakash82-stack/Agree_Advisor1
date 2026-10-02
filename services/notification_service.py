import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from database.database import db
from database.models import Notification, User, Device
from config import Config

class NotificationService:
    """Manages notification persistence, deduplication cooldowns, and email dispatch."""

    COOLDOWN_MINUTES = 15

    @classmethod
    def create_notification(cls, user_id: int, title: str, message: str, notif_type: str = "system") -> bool:
        """
        Creates a notification with deduplication.
        If an identical notification was generated for this user in the last COOLDOWN_MINUTES, skips.
        """
        now = datetime.now(timezone.utc)
        cooldown_threshold = now - timedelta(minutes=cls.COOLDOWN_MINUTES)

        # Check for recent duplicate
        existing = Notification.query.filter(
            Notification.user_id == user_id,
            Notification.title == title,
            Notification.created_at >= cooldown_threshold
        ).first()

        if existing:
            return False # Skip duplicate to prevent spam

        # Create new record
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type,
            is_read=False,
            created_at=now
        )
        db.session.add(notif)
        db.session.commit()

        # Trigger email if configured and enabled
        user = db.session.get(User, user_id)
        if user and user.notification_enabled and user.email_notifications:
            cls.send_email_notification(user.email, title, message)

        return True

    @classmethod
    def broadcast_alert(cls, title: str, message: str, notif_type: str = "sensor"):
        """Broadcasts an alert to all registered users who have the relevant alert setting enabled."""
        users = User.query.filter_by(notification_enabled=True).all()
        for u in users:
            should_send = True
            if notif_type == "sensor" and not u.sensor_alerts:
                should_send = False
            elif notif_type == "soil" and not u.soil_alerts:
                should_send = False
            elif notif_type == "crop" and not u.crop_alerts:
                should_send = False
            elif notif_type == "system" and not u.system_alerts:
                should_send = False

            if should_send:
                cls.create_notification(u.id, title, message, notif_type)

    @classmethod
    def evaluate_telemetry_alerts(cls, reading_data: dict, device_id: str):
        """Evaluates soil reading values against thresholds and creates alerts if necessary."""
        thresholds = Config.SOIL_PARAM_THRESHOLDS
        
        # 1. Moisture
        m_val = float(reading_data.get("moisture", 50.0))
        m_cfg = thresholds["moisture"]
        if m_val < m_cfg["low"]:
            cls.broadcast_alert(
                f"LOW MOISTURE: {device_id}",
                f"Soil moisture at {device_id} is low ({m_val}%). Consider irrigation.",
                "soil"
            )
        elif m_val > m_cfg["high"]:
            cls.broadcast_alert(
                f"HIGH MOISTURE: {device_id}",
                f"Soil moisture at {device_id} is elevated ({m_val}%). Check field drainage.",
                "soil"
            )

        # 2. pH
        ph_val = float(reading_data.get("ph", 6.5))
        ph_cfg = thresholds["ph"]
        if ph_val < ph_cfg["normal_min"] or ph_val > ph_cfg["normal_max"]:
            cls.broadcast_alert(
                f"ABNORMAL pH: {device_id}",
                f"Soil pH at {device_id} is outside target range ({ph_val}). Evaluate lime/gypsum application.",
                "soil"
            )

        # 3. Nitrogen
        n_val = float(reading_data.get("nitrogen", 40.0))
        n_cfg = thresholds["nitrogen"]
        if n_val < n_cfg["low"]:
            cls.broadcast_alert(
                f"LOW NITROGEN: {device_id}",
                f"Nitrogen is below target optimum ({n_val} mg/kg). Nutrient replenishment advisable.",
                "soil"
            )

        # 4. EC (Salinity)
        ec_val = float(reading_data.get("ec", 1200.0))
        ec_cfg = thresholds["ec"]
        if ec_val > ec_cfg["high"]:
            cls.broadcast_alert(
                f"HIGH SALINITY / EC: {device_id}",
                f"Electrical Conductivity is high ({ec_val} µS/cm). Salt stress warning.",
                "soil"
            )

    @classmethod
    def send_email_notification(cls, to_email: str, subject: str, body: str) -> bool:
        """Sends an email notification via SMTP if credentials are configured."""
        if not Config.MAIL_ENABLED or not Config.MAIL_SERVER:
            # Gracefully ignore if not configured
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = Config.MAIL_FROM
            msg['To'] = to_email
            msg['Subject'] = f"[Smart Soil Alert] {subject}"
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=5)
            server.starttls()
            if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"[Email Notification Notice] Could not dispatch email: {e}")
            return False
