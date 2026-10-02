from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()

def run_migrations():
    """Safely adds missing columns to existing SQLite database without dropping tables or losing telemetry data."""
    try:
        engine = db.engine
        with engine.connect() as conn:
            # 1. Check columns in 'users' table
            user_cols_res = conn.execute(text("PRAGMA table_info(users)"))
            existing_user_cols = {row[1] for row in user_cols_res.fetchall()}

            user_columns_to_add = [
                ("google_id", "VARCHAR(128)"),
                ("name", "VARCHAR(128)"),
                ("email", "VARCHAR(128)"),
                ("profile_picture", "VARCHAR(512)"),
                ("mobile_number", "VARCHAR(32)"),
                ("location", "VARCHAR(128)"),
                ("address", "VARCHAR(255)"),
                ("city", "VARCHAR(64)"),
                ("state", "VARCHAR(64)"),
                ("country", "VARCHAR(64) DEFAULT 'India'"),
                ("pincode", "VARCHAR(16)"),
                ("role", "VARCHAR(16) DEFAULT 'USER'"),
                ("theme_preference", "VARCHAR(16) DEFAULT 'system'"),
                ("notification_enabled", "BOOLEAN DEFAULT 1"),
                ("email_notifications", "BOOLEAN DEFAULT 0"),
                ("browser_notifications", "BOOLEAN DEFAULT 0"),
                ("sensor_alerts", "BOOLEAN DEFAULT 1"),
                ("soil_alerts", "BOOLEAN DEFAULT 1"),
                ("crop_alerts", "BOOLEAN DEFAULT 1"),
                ("system_alerts", "BOOLEAN DEFAULT 1"),
                ("updated_at", "DATETIME"),
                ("last_login", "DATETIME")
            ]

            for col_name, col_type in user_columns_to_add:
                if col_name not in existing_user_cols:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                    conn.commit()

            # 2. Check columns in 'devices' table
            dev_cols_res = conn.execute(text("PRAGMA table_info(devices)"))
            existing_dev_cols = {row[1] for row in dev_cols_res.fetchall()}

            if "user_id" not in existing_dev_cols:
                conn.execute(text("ALTER TABLE devices ADD COLUMN user_id INTEGER"))
                conn.commit()

    except Exception as e:
        print(f"[Migration Notice] Non-fatal migration check: {e}")

def init_db(app):
    """Initializes SQLAlchemy with the Flask application and executes non-destructive migrations."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        run_migrations()
