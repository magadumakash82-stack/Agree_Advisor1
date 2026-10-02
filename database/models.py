from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from .database import db

class User(db.Model):
    """User profile and Google OAuth authentication model."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(128), unique=True, nullable=True, index=True)
    name = db.Column(db.String(128), nullable=True)
    email = db.Column(db.String(128), unique=True, nullable=False, index=True)
    username = db.Column(db.String(64), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True) # Nullable: Google OAuth does not store passwords
    profile_picture = db.Column(db.String(512), nullable=True)
    mobile_number = db.Column(db.String(32), nullable=True)
    location = db.Column(db.String(128), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(64), nullable=True)
    state = db.Column(db.String(64), nullable=True)
    country = db.Column(db.String(64), nullable=True, default="India")
    pincode = db.Column(db.String(16), nullable=True)
    role = db.Column(db.String(16), default="USER", nullable=False) # "USER" or "ADMIN"
    
    # Preferences & Settings
    theme_preference = db.Column(db.String(16), default="system", nullable=False) # "light", "dark", "system"
    notification_enabled = db.Column(db.Boolean, default=True, nullable=False)
    email_notifications = db.Column(db.Boolean, default=False, nullable=False)
    browser_notifications = db.Column(db.Boolean, default=False, nullable=False)
    sensor_alerts = db.Column(db.Boolean, default=True, nullable=False)
    soil_alerts = db.Column(db.Boolean, default=True, nullable=False)
    crop_alerts = db.Column(db.Boolean, default=True, nullable=False)
    system_alerts = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_display_name(self):
        return self.name or self.username or self.email.split('@')[0]

    def get_initials(self):
        name = self.get_display_name().strip()
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        elif len(parts) == 1 and len(parts[0]) >= 2:
            return parts[0][:2].upper()
        return "U"

    def is_admin(self):
        return self.role == "ADMIN"

    def to_dict(self):
        return {
            "id": self.id,
            "google_id": self.google_id,
            "name": self.name or "",
            "display_name": self.get_display_name(),
            "email": self.email,
            "profile_picture": self.profile_picture or "",
            "initials": self.get_initials(),
            "mobile_number": self.mobile_number or "",
            "location": self.location or "",
            "address": self.address or "",
            "city": self.city or "",
            "state": self.state or "",
            "country": self.country or "India",
            "pincode": self.pincode or "",
            "role": self.role,
            "theme_preference": self.theme_preference,
            "notification_enabled": self.notification_enabled,
            "email_notifications": self.email_notifications,
            "browser_notifications": self.browser_notifications,
            "sensor_alerts": self.sensor_alerts,
            "soil_alerts": self.soil_alerts,
            "crop_alerts": self.crop_alerts,
            "system_alerts": self.system_alerts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

    def to_settings_dict(self):
        return {
            "theme": self.theme_preference,
            "notifications_enabled": self.notification_enabled,
            "sensor_alerts": self.sensor_alerts,
            "soil_alerts": self.soil_alerts,
            "crop_alerts": self.crop_alerts,
            "system_alerts": self.system_alerts,
            "email_notifications": self.email_notifications,
            "browser_notifications": self.browser_notifications
        }


class Device(db.Model):
    """IoT device registry model with user ownership."""
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    device_name = db.Column(db.String(128), nullable=False)
    location = db.Column(db.String(255), nullable=True, default="Field Sensor")
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), default="OFFLINE")
    last_seen = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    owner = db.relationship('User', backref=db.backref('devices', lazy=True))

    def is_online(self, timeout_seconds=30):
        if not self.last_seen:
            return False
        now = datetime.now(timezone.utc)
        last = self.last_seen
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (now - last).total_seconds() <= timeout_seconds

    def to_dict(self, timeout_seconds=30):
        online = self.is_online(timeout_seconds)
        last_str = self.last_seen.isoformat() if self.last_seen else None
        return {
            "id": self.id,
            "device_id": self.device_id,
            "user_id": self.user_id,
            "owner_name": self.owner.get_display_name() if self.owner else "System (Unassigned)",
            "device_name": self.device_name,
            "location": self.location,
            "description": self.description or "",
            "status": "ONLINE" if online else "OFFLINE",
            "is_online": online,
            "last_seen": last_str,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Notification(db.Model):
    """User notifications and telemetry alert center."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    title = db.Column(db.String(128), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(32), default="system", nullable=False) # sensor, soil, crop, system
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))

    def to_dict(self):
        ts = self.created_at
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "created_at": ts.isoformat() if ts else None,
            "formatted_time": ts.strftime("%b %d, %H:%M") if ts else ""
        }


class SoilReading(db.Model):
    """7-in-1 Soil Sensor telemetry records."""
    __tablename__ = 'soil_readings'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(64), nullable=False, index=True)
    moisture = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    ec = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    nitrogen = db.Column(db.Float, nullable=False)
    phosphorus = db.Column(db.Float, nullable=False)
    potassium = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    is_simulated = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        ts = self.timestamp
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return {
            "id": self.id,
            "device_id": self.device_id,
            "moisture": round(float(self.moisture), 2),
            "temperature": round(float(self.temperature), 2),
            "ec": round(float(self.ec), 2),
            "ph": round(float(self.ph), 2),
            "nitrogen": round(float(self.nitrogen), 2),
            "phosphorus": round(float(self.phosphorus), 2),
            "potassium": round(float(self.potassium), 2),
            "timestamp": ts.isoformat() if ts else None,
            "formatted_time": ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "N/A",
            "is_simulated": bool(self.is_simulated)
        }


class SystemSetting(db.Model):
    """Application and threshold configuration settings."""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)

    @classmethod
    def get_val(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set_val(cls, key, value):
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key, value=str(value))
            db.session.add(setting)
        else:
            setting.value = str(value)
        db.session.commit()
