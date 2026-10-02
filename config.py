import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load .env file if it exists
load_dotenv(BASE_DIR / ".env")

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "smart_soil_secure_secret_key_change_in_production_2026")
    
    # Database configuration (SQLite by default, compatible with PostgreSQL)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'soil.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # IoT Device Security
    API_KEY = os.getenv("API_KEY", "CHANGE_THIS")
    
    # Device offline timeout in seconds (Default 30 seconds as specified)
    DEVICE_OFFLINE_TIMEOUT = int(os.getenv("DEVICE_OFFLINE_TIMEOUT", "30"))

    # Google OAuth 2.0 / OpenID Connect Configuration
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "CHANGE_THIS")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "CHANGE_THIS")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:5000/auth/google/callback")

    # Email Notification Configuration (Optional)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@smartsoil.org")
    MAIL_ENABLED = os.getenv("MAIL_ENABLED", "0") == "1"

    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Reports output directory
    REPORTS_DIR = BASE_DIR / "reports"
    
    # Data directory
    DATA_DIR = BASE_DIR / "data"

    # Default admin credentials for fallback / initial seeding
    DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "CHANGE_THIS")

    # Agronomic parameter standard reference bounds
    # (Low, Normal Min, Normal Max, High)
    SOIL_PARAM_THRESHOLDS = {
        "moisture": {
            "name": "Soil Moisture",
            "unit": "%",
            "critical_low": 20.0,
            "low": 35.0,
            "normal_min": 40.0,
            "normal_max": 75.0,
            "high": 85.0,
            "critical_high": 95.0
        },
        "temperature": {
            "name": "Soil Temperature",
            "unit": "°C",
            "critical_low": 10.0,
            "low": 18.0,
            "normal_min": 20.0,
            "normal_max": 32.0,
            "high": 36.0,
            "critical_high": 42.0
        },
        "ec": {
            "name": "Electrical Conductivity",
            "unit": "µS/cm",
            "critical_low": 200.0,
            "low": 500.0,
            "normal_min": 700.0,
            "normal_max": 2000.0,
            "high": 2500.0,
            "critical_high": 4000.0
        },
        "ph": {
            "name": "Soil pH",
            "unit": "pH scale",
            "critical_low": 4.5,
            "low": 5.5,
            "normal_min": 6.0,
            "normal_max": 7.5,
            "high": 8.0,
            "critical_high": 9.0
        },
        "nitrogen": {
            "name": "Nitrogen (N)",
            "unit": "mg/kg",
            "critical_low": 15.0,
            "low": 25.0,
            "normal_min": 35.0,
            "normal_max": 75.0,
            "high": 90.0,
            "critical_high": 120.0
        },
        "phosphorus": {
            "name": "Phosphorus (P)",
            "unit": "mg/kg",
            "critical_low": 10.0,
            "low": 20.0,
            "normal_min": 25.0,
            "normal_max": 50.0,
            "high": 60.0,
            "critical_high": 80.0
        },
        "potassium": {
            "name": "Potassium (K)",
            "unit": "mg/kg",
            "critical_low": 15.0,
            "low": 30.0,
            "normal_min": 40.0,
            "normal_max": 80.0,
            "high": 100.0,
            "critical_high": 130.0
        }
    }
