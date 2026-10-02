import os
import socket
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify
from config import Config
from database.database import db, init_db
from database.models import User, Device, SoilReading, SystemSetting
from routes.api import api_bp
from routes.auth import auth_bp, ensure_default_user
from routes.web import web_bp
from services.crop_optimizer import CropOptimizerService

def create_app():
    """Application factory for Smart Soil Testing & Crop Optimization System."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure reports directory exists
    os.makedirs(Config.REPORTS_DIR, exist_ok=True)

    # Initialize Database
    init_db(app)

    # Register Blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(web_bp)

    with app.app_context():
        # Ensure default admin user
        ensure_default_user()

        # Seed initial device if table is empty
        if Device.query.count() == 0:
            primary_device = Device(
                device_id="SOIL_001",
                device_name="Primary Farm Sensor",
                location="North Plot - Section A",
                description="RS485 7-in-1 NPK + pH + EC + Moisture + Temperature Sensor",
                status="OFFLINE",
                last_seen=None
            )
            db.session.add(primary_device)
            db.session.commit()

        # Preload crops catalog
        CropOptimizerService.load_crops()

        # Seed initial baseline telemetry record if empty
        if SoilReading.query.count() == 0:
            initial_time = datetime.now(timezone.utc)
            init_reading = SoilReading(
                device_id="SOIL_001",
                moisture=48.6,
                temperature=34.1,
                ec=1500.0,
                ph=6.5,
                nitrogen=32.0,
                phosphorus=37.0,
                potassium=48.0,
                timestamp=initial_time,
                is_simulated=True
            )
            db.session.add(init_reading)
            db.session.commit()

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html', error=str(e)), 500

    return app

# Top-level Flask application instance (required by `flask run`, WSGI, and deployment servers)
app = create_app()
application = app

def get_local_ip():
    """Attempts to find the local LAN IP address of this computer."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == '__main__':
    local_ip = get_local_ip()
    port = int(os.getenv("PORT", 5000))
    
    print("\n" + "=" * 70)
    print("  AgriAdvisor: Smart Soil Testing & Crop Optimization System")
    print("  IoT-Based Soil Monitoring, Analysis and Crop Suitability Platform")
    print("=" * 70)
    print(f"  * Web Dashboard:  http://localhost:{port}")
    print(f"  * Local LAN URL:  http://{local_ip}:{port}")
    print(f"  * ESP32 Endpoint: http://{local_ip}:{port}/api/soil-data")
    print(f"  * Default User:   admin")
    print(f"  * Default Pass:   CHANGE_THIS")
    print("=" * 70 + "\n")

    app.run(host='0.0.0.0', port=port, debug=True)
