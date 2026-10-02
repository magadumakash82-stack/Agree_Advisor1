import csv
import io
import math
import random
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, Response, send_file, current_app, session
from database.database import db
from database.models import SoilReading, Device, SystemSetting, User, Notification
from services.soil_analysis import SoilAnalysisService
from services.crop_optimizer import CropOptimizerService
from services.report_generator import ReportGeneratorService
from services.notification_service import NotificationService
from config import Config

api_bp = Blueprint('api', __name__, url_prefix='/api')

def get_configured_api_key():
    val = SystemSetting.get_val("api_key")
    return val if val is not None else Config.API_KEY

def get_offline_timeout():
    val = SystemSetting.get_val("device_offline_timeout")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return Config.DEVICE_OFFLINE_TIMEOUT

def validate_number(val, name, min_val=-50.0, max_val=100000.0):
    """Strict numeric validation rejecting None, non-numeric strings, NaN, Inf."""
    if val is None:
        raise ValueError(f"Field '{name}' cannot be null.")
    try:
        f_val = float(val)
    except (ValueError, TypeError):
        raise ValueError(f"Field '{name}' must be a valid number, got {val}.")
    if math.isnan(f_val) or math.isinf(f_val):
        raise ValueError(f"Field '{name}' cannot be NaN or Infinite.")
    if f_val < min_val or f_val > max_val:
        raise ValueError(f"Field '{name}' value {f_val} is out of realistic physical range [{min_val}, {max_val}].")
    return f_val

@api_bp.route('/soil-data', methods=['POST'])
def receive_soil_data():
    """
    POST /api/soil-data
    Ingests soil telemetry data from ESP32 or simulated test generator.
    Requires X-API-Key header unless authorized session or internal test mode.
    """
    api_key_header = request.headers.get("X-API-Key")
    configured_key = get_configured_api_key()

    # Allow authenticated web session or valid API key
    is_session_auth = session.get('user_id') is not None
    if not is_session_auth:
        if not api_key_header or api_key_header != configured_key:
            return jsonify({
                "status": "error",
                "message": "Unauthorized: Invalid or missing X-API-Key header"
            }), 401

    if not request.is_json:
        return jsonify({
            "status": "error",
            "message": "Invalid soil data: Request body must be valid JSON"
        }), 400

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Invalid soil data: Malformed JSON payload"
        }), 400

    # Validate required parameters
    required_fields = ["device_id", "moisture", "temperature", "ec", "ph", "nitrogen", "phosphorus", "potassium"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({
            "status": "error",
            "message": f"Invalid soil data: Missing required fields: {', '.join(missing)}"
        }), 400

    device_id = str(data["device_id"]).strip()
    if not device_id:
        return jsonify({
            "status": "error",
            "message": "Invalid soil data: device_id cannot be blank"
        }), 400

    try:
        moisture = validate_number(data["moisture"], "moisture", 0.0, 100.0)
        temperature = validate_number(data["temperature"], "temperature", -20.0, 80.0)
        ec = validate_number(data["ec"], "ec", 0.0, 20000.0)
        ph = validate_number(data["ph"], "ph", 0.0, 14.0)
        nitrogen = validate_number(data["nitrogen"], "nitrogen", 0.0, 1000.0)
        phosphorus = validate_number(data["phosphorus"], "phosphorus", 0.0, 1000.0)
        potassium = validate_number(data["potassium"], "potassium", 0.0, 1000.0)
    except ValueError as ve:
        return jsonify({
            "status": "error",
            "message": "Invalid soil data",
            "details": str(ve)
        }), 400

    is_simulated = bool(data.get("is_simulated", False))
    now = datetime.now(timezone.utc)

    try:
        # Update or register device
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            device = Device(
                device_id=device_id,
                device_name=f"Device {device_id}",
                location="Field Sector 1",
                description="Auto-registered IoT Soil Sensor",
                status="ONLINE",
                last_seen=now
            )
            db.session.add(device)
        else:
            device.last_seen = now
            device.status = "ONLINE"

        # Create reading record
        reading = SoilReading(
            device_id=device_id,
            moisture=moisture,
            temperature=temperature,
            ec=ec,
            ph=ph,
            nitrogen=nitrogen,
            phosphorus=phosphorus,
            potassium=potassium,
            timestamp=now,
            is_simulated=is_simulated
        )
        db.session.add(reading)
        db.session.commit()

        # Evaluate alerts & trigger notifications (with deduplication)
        try:
            NotificationService.evaluate_telemetry_alerts(reading.to_dict(), device_id)
        except Exception as alert_err:
            print(f"[Alert Evaluation Notice] {alert_err}")

        return jsonify({
            "status": "success",
            "message": "Soil data received",
            "id": reading.id,
            "timestamp": now.isoformat()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Database error while storing soil data",
            "details": str(e)
        }), 500

@api_bp.route('/latest-soil-data', methods=['GET'])
def get_latest_soil_data():
    """
    GET /api/latest-soil-data
    Returns the latest sensor reading, online status, trend indicators, and health analysis.
    """
    device_id = request.args.get('device_id')
    timeout_sec = get_offline_timeout()

    query = SoilReading.query
    if device_id:
        query = query.filter_by(device_id=device_id)

    # Get the latest reading
    latest = query.order_by(SoilReading.timestamp.desc()).first()

    if not latest:
        return jsonify({
            "status": "empty",
            "message": "No soil data available yet.",
            "data": None,
            "is_online": False,
            "device_status": "OFFLINE"
        }), 200

    # Get the previous reading to calculate trends
    prev = SoilReading.query.filter(
        SoilReading.device_id == latest.device_id,
        SoilReading.id < latest.id
    ).order_by(SoilReading.timestamp.desc()).first()

    # Calculate time difference
    now = datetime.now(timezone.utc)
    latest_time = latest.timestamp
    if latest_time.tzinfo is None:
        latest_time = latest_time.replace(tzinfo=timezone.utc)

    seconds_ago = int((now - latest_time).total_seconds())
    is_online = seconds_ago <= timeout_sec

    # Parameter trends (up, down, stable)
    trends = {}
    param_keys = ["moisture", "temperature", "ec", "ph", "nitrogen", "phosphorus", "potassium"]
    for p in param_keys:
        curr_val = getattr(latest, p)
        if prev:
            prev_val = getattr(prev, p)
            diff = curr_val - prev_val
            if abs(diff) < 0.05:
                direction = "stable"
            elif diff > 0:
                direction = "up"
            else:
                direction = "down"
            trends[p] = {"direction": direction, "delta": round(diff, 2)}
        else:
            trends[p] = {"direction": "stable", "delta": 0.0}

    # Run soil analysis
    reading_dict = latest.to_dict()
    analysis = SoilAnalysisService.evaluate_reading(reading_dict)

    response_data = {
        "status": "success",
        "device_id": latest.device_id,
        "moisture": latest.moisture,
        "temperature": latest.temperature,
        "ec": latest.ec,
        "ph": latest.ph,
        "nitrogen": latest.nitrogen,
        "phosphorus": latest.phosphorus,
        "potassium": latest.potassium,
        "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
        "formatted_time": latest_time.strftime("%Y-%m-%d %H:%M:%S"),
        "seconds_ago": max(0, seconds_ago),
        "is_online": is_online,
        "device_status": "ONLINE" if is_online else "OFFLINE",
        "is_simulated": latest.is_simulated,
        "trends": trends,
        "health_analysis": analysis
    }

    return jsonify(response_data), 200

@api_bp.route('/soil-history', methods=['GET'])
def get_soil_history():
    """
    GET /api/soil-history
    Returns historical data filtered by range (24h, 7d, 30d, custom) for Chart.js.
    """
    time_range = request.args.get('range', '24h')
    device_id = request.args.get('device_id')
    now = datetime.now(timezone.utc)

    query = SoilReading.query

    if device_id:
        query = query.filter_by(device_id=device_id)

    if time_range == '24h':
        start_time = now - timedelta(hours=24)
        query = query.filter(SoilReading.timestamp >= start_time)
    elif time_range == '7d':
        start_time = now - timedelta(days=7)
        query = query.filter(SoilReading.timestamp >= start_time)
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
        query = query.filter(SoilReading.timestamp >= start_time)
    elif time_range == 'custom':
        start_str = request.args.get('start_date')
        end_str = request.args.get('end_date')
        if start_str:
            try:
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                query = query.filter(SoilReading.timestamp >= start_dt)
            except Exception:
                pass
        if end_str:
            try:
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                query = query.filter(SoilReading.timestamp <= end_dt)
            except Exception:
                pass

    # Order ascending for sequential time series plotting
    records = query.order_by(SoilReading.timestamp.asc()).limit(500).all()

    timestamps = []
    moisture = []
    temperature = []
    ec = []
    ph = []
    nitrogen = []
    phosphorus = []
    potassium = []

    for r in records:
        ts = r.timestamp
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        timestamps.append(ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "")
        moisture.append(round(r.moisture, 2))
        temperature.append(round(r.temperature, 2))
        ec.append(round(r.ec, 2))
        ph.append(round(r.ph, 2))
        nitrogen.append(round(r.nitrogen, 2))
        phosphorus.append(round(r.phosphorus, 2))
        potassium.append(round(r.potassium, 2))

    return jsonify({
        "status": "success",
        "count": len(records),
        "timestamps": timestamps,
        "series": {
            "moisture": moisture,
            "temperature": temperature,
            "ec": ec,
            "ph": ph,
            "nitrogen": nitrogen,
            "phosphorus": phosphorus,
            "potassium": potassium
        }
    }), 200

@api_bp.route('/readings-table', methods=['GET'])
def get_readings_table():
    """Paginated readings for the Data Table component."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)
    search = request.args.get('search', '').strip()
    device_id = request.args.get('device_id', '').strip()

    query = SoilReading.query
    if device_id:
        query = query.filter_by(device_id=device_id)
    if search:
        query = query.filter(SoilReading.device_id.ilike(f"%{search}%"))

    pagination = query.order_by(SoilReading.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "status": "success",
        "items": [r.to_dict() for r in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "per_page": pagination.per_page,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    }), 200

@api_bp.route('/system-status', methods=['GET'])
def get_system_status():
    """
    GET /api/system-status
    High-level real-time status bar telemetry.
    """
    timeout_sec = get_offline_timeout()
    latest = SoilReading.query.order_by(SoilReading.timestamp.desc()).first()

    db_status = "CONNECTED"
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        db_status = "DISCONNECTED"

    demo_mode_state = SystemSetting.get_val("demo_mode_active", "0") == "1"

    if latest:
        now = datetime.now(timezone.utc)
        latest_time = latest.timestamp
        if latest_time.tzinfo is None:
            latest_time = latest_time.replace(tzinfo=timezone.utc)
        seconds_ago = int((now - latest_time).total_seconds())
        esp32_status = "ONLINE" if seconds_ago <= timeout_sec else "OFFLINE"
        wifi_status = "CONNECTED" if seconds_ago <= timeout_sec else "DISCONNECTED"
        sensor_status = "ACTIVE" if seconds_ago <= timeout_sec else "INACTIVE"
        active_device = latest.device_id
        is_simulated = latest.is_simulated
    else:
        seconds_ago = None
        esp32_status = "OFFLINE"
        wifi_status = "DISCONNECTED"
        sensor_status = "INACTIVE"
        active_device = "None"
        is_simulated = False

    return jsonify({
        "esp32": esp32_status,
        "wifi": wifi_status,
        "api": "ONLINE",
        "database": db_status,
        "sensor": sensor_status,
        "last_sync_seconds_ago": seconds_ago,
        "active_device": active_device,
        "is_demo_active": demo_mode_state,
        "is_latest_simulated": is_simulated,
        "offline_timeout": timeout_sec
    }), 200

@api_bp.route('/devices', methods=['GET', 'POST'])
def handle_devices():
    """List or add devices."""
    timeout_sec = get_offline_timeout()
    if request.method == 'POST':
        if not request.is_json:
            return jsonify({"status": "error", "message": "Expected JSON payload"}), 400
        data = request.get_json()
        dev_id = str(data.get("device_id", "")).strip()
        dev_name = str(data.get("device_name", "")).strip()
        location = str(data.get("location", "")).strip()
        description = str(data.get("description", "")).strip()

        if not dev_id or not dev_name:
            return jsonify({"status": "error", "message": "Device ID and Device Name are required"}), 400

        existing = Device.query.filter_by(device_id=dev_id).first()
        if existing:
            return jsonify({"status": "error", "message": f"Device with ID '{dev_id}' already exists"}), 409

        device = Device(
            device_id=dev_id,
            user_id=session.get('user_id'),
            device_name=dev_name,
            location=location,
            description=description,
            status="OFFLINE"
        )
        db.session.add(device)
        db.session.commit()
        return jsonify({"status": "success", "message": "Device registered successfully", "device": device.to_dict(timeout_sec)}), 201

    devices = Device.query.order_by(Device.created_at.desc()).all()
    return jsonify({
        "status": "success",
        "devices": [d.to_dict(timeout_sec) for d in devices]
    }), 200

@api_bp.route('/crops/recommendations', methods=['GET', 'POST'])
def get_crop_recommendations():
    """
    Evaluates crop suitability against the latest reading or custom soil parameters.
    """
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
    else:
        # Default to latest reading
        latest = SoilReading.query.order_by(SoilReading.timestamp.desc()).first()
        if latest:
            data = latest.to_dict()
        else:
            # Standard neutral fallback if completely empty
            data = {
                "moisture": 50.0,
                "temperature": 25.0,
                "ec": 1200.0,
                "ph": 6.5,
                "nitrogen": 45.0,
                "phosphorus": 35.0,
                "potassium": 50.0
            }

    results = CropOptimizerService.evaluate_all(data)
    return jsonify(results), 200

@api_bp.route('/demo/toggle', methods=['POST'])
def toggle_demo():
    """Toggles Demo Mode state."""
    data = request.get_json(silent=True) or {}
    new_state = data.get("enabled")
    if new_state is None:
        curr = SystemSetting.get_val("demo_mode_active", "0") == "1"
        new_state = not curr

    SystemSetting.set_val("demo_mode_active", "1" if new_state else "0")
    return jsonify({
        "status": "success",
        "demo_mode": bool(new_state),
        "message": "Demo mode activated. Simulated telemetry enabled." if new_state else "Demo mode stopped."
    }), 200

@api_bp.route('/demo/generate-reading', methods=['POST'])
def generate_demo_reading():
    """Generates a single realistic simulated reading with random variation for demonstrations."""
    # Base realistic loam soil values
    base_moisture = 48.0 + random.uniform(-6.0, 6.0)
    base_temp = 28.0 + random.uniform(-2.5, 3.5)
    base_ec = 1450.0 + random.uniform(-150.0, 150.0)
    base_ph = 6.6 + random.uniform(-0.4, 0.4)
    base_n = 42.0 + random.uniform(-8.0, 8.0)
    base_p = 34.0 + random.uniform(-5.0, 5.0)
    base_k = 52.0 + random.uniform(-7.0, 7.0)

    now = datetime.now(timezone.utc)
    device_id = "SOIL_DEMO_01"

    # Ensure demo device exists
    dev = Device.query.filter_by(device_id=device_id).first()
    if not dev:
        dev = Device(
            device_id=device_id,
            device_name="Demo Field Sensor (Simulation)",
            location="Demonstration Sandbox",
            description="Virtual sensor for laboratory testing and demonstrations",
            status="ONLINE",
            last_seen=now
        )
        db.session.add(dev)
    else:
        dev.last_seen = now
        dev.status = "ONLINE"

    reading = SoilReading(
        device_id=device_id,
        moisture=round(base_moisture, 1),
        temperature=round(base_temp, 1),
        ec=round(base_ec, 0),
        ph=round(base_ph, 2),
        nitrogen=round(base_n, 1),
        phosphorus=round(base_p, 1),
        potassium=round(base_k, 1),
        timestamp=now,
        is_simulated=True
    )
    db.session.add(reading)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Simulated reading generated",
        "reading": reading.to_dict()
    }), 201

@api_bp.route('/export/csv', methods=['GET'])
def export_csv():
    """Exports soil readings to CSV file with standard headers."""
    device_id = request.args.get('device_id')
    query = SoilReading.query
    if device_id:
        query = query.filter_by(device_id=device_id)

    readings = query.order_by(SoilReading.timestamp.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp",
        "device_id",
        "moisture",
        "temperature",
        "ec",
        "ph",
        "nitrogen",
        "phosphorus",
        "potassium",
        "is_simulated"
    ])

    for r in readings:
        ts = r.timestamp
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        writer.writerow([
            ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "",
            r.device_id,
            r.moisture,
            r.temperature,
            r.ec,
            r.ph,
            r.nitrogen,
            r.phosphorus,
            r.potassium,
            "true" if r.is_simulated else "false"
        ])

    output.seek(0)
    filename = f"soil_telemetry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@api_bp.route('/export/pdf', methods=['GET'])
def export_pdf():
    """Generates and downloads the official PDF soil health & crop optimization report."""
    device_id = request.args.get('device_id')
    query = SoilReading.query
    if device_id:
        query = query.filter_by(device_id=device_id)

    latest = query.order_by(SoilReading.timestamp.desc()).first()
    if not latest:
        # Fallback reading
        latest_data = {
            "device_id": "SOIL_001",
            "moisture": 48.6,
            "temperature": 28.5,
            "ec": 1400.0,
            "ph": 6.5,
            "nitrogen": 40.0,
            "phosphorus": 32.0,
            "potassium": 50.0,
            "formatted_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "is_simulated": False
        }
        device_info = {
            "device_id": "SOIL_001",
            "device_name": "Field Sensor 1",
            "location": "Agricultural Plot A"
        }
    else:
        latest_data = latest.to_dict()
        dev = Device.query.filter_by(device_id=latest.device_id).first()
        device_info = dev.to_dict() if dev else {
            "device_id": latest.device_id,
            "device_name": f"Sensor {latest.device_id}",
            "location": "Main Field"
        }

    health_analysis = SoilAnalysisService.evaluate_reading(latest_data)
    crop_results = CropOptimizerService.evaluate_all(latest_data)

    pdf_buffer = ReportGeneratorService.generate_pdf(device_info, latest_data, health_analysis, crop_results)
    filename = f"soil_report_{latest_data['device_id']}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

# =========================================================================
# PROFILE API (SECTION 28)
# =========================================================================

@api_bp.route('/profile', methods=['GET'])
def get_user_profile():
    """GET /api/profile: Returns authenticated user profile."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    return jsonify(user.to_dict()), 200

@api_bp.route('/profile', methods=['PUT'])
def update_user_profile():
    """PUT /api/profile: Updates editable user profile fields. Does not permit changing google_id or email."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json(silent=True) or {}

    if 'name' in data and data['name'].strip():
        user.name = data['name'].strip()
        session['name'] = user.get_display_name()

    if 'mobile_number' in data:
        user.mobile_number = data['mobile_number'].strip()

    if 'location' in data:
        user.location = data['location'].strip()

    if 'address' in data:
        user.address = data['address'].strip()

    if 'city' in data:
        user.city = data['city'].strip()

    if 'state' in data:
        user.state = data['state'].strip()

    if 'country' in data:
        user.country = data['country'].strip()

    if 'pincode' in data:
        user.pincode = data['pincode'].strip()

    user.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    # Dismiss onboarding modal if filled
    if user.mobile_number and user.address:
        session.pop('show_onboarding', None)

    return jsonify({
        "status": "success",
        "message": "Profile updated successfully",
        "profile": user.to_dict()
    }), 200

# =========================================================================
# SETTINGS API (SECTION 27 & 29)
# =========================================================================

@api_bp.route('/settings', methods=['GET'])
def get_user_settings():
    """GET /api/settings: Returns current user settings."""
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None

    if user:
        return jsonify(user.to_settings_dict()), 200

    # Default response if unauthenticated
    return jsonify({
        "theme": "system",
        "notifications_enabled": True,
        "sensor_alerts": True,
        "soil_alerts": True,
        "crop_alerts": True,
        "system_alerts": True,
        "email_notifications": False,
        "browser_notifications": False
    }), 200

@api_bp.route('/settings', methods=['PUT'])
def update_user_settings():
    """PUT /api/settings: Updates appearance and notification preferences."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json(silent=True) or {}

    if 'theme' in data and data['theme'] in ['light', 'dark', 'system']:
        user.theme_preference = data['theme']
        session['theme'] = data['theme']

    if 'notifications_enabled' in data:
        user.notification_enabled = bool(data['notifications_enabled'])

    if 'sensor_alerts' in data:
        user.sensor_alerts = bool(data['sensor_alerts'])

    if 'soil_alerts' in data:
        user.soil_alerts = bool(data['soil_alerts'])

    if 'crop_alerts' in data:
        user.crop_alerts = bool(data['crop_alerts'])

    if 'system_alerts' in data:
        user.system_alerts = bool(data['system_alerts'])

    if 'email_notifications' in data:
        user.email_notifications = bool(data['email_notifications'])

    if 'browser_notifications' in data:
        user.browser_notifications = bool(data['browser_notifications'])

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Preferences saved successfully",
        "settings": user.to_settings_dict()
    }), 200

# =========================================================================
# NOTIFICATIONS API (SECTION 14, 15, 27)
# =========================================================================

@api_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """GET /api/notifications: Returns notifications for current user."""
    user_id = session.get('user_id')
    query = Notification.query

    if user_id:
        query = query.filter((Notification.user_id == user_id) | (Notification.user_id.is_(None)))

    notifs = query.order_by(Notification.created_at.desc()).limit(50).all()
    unread_count = sum(1 for n in notifs if not n.is_read)

    return jsonify({
        "status": "success",
        "unread_count": unread_count,
        "items": [n.to_dict() for n in notifs]
    }), 200

@api_bp.route('/notifications/<int:notif_id>/read', methods=['PUT', 'POST'])
def mark_notification_read(notif_id):
    """PUT /api/notifications/<id>/read: Marks notification as read."""
    notif = db.session.get(Notification, notif_id)
    if not notif:
        return jsonify({"status": "error", "message": "Notification not found"}), 404

    notif.is_read = True
    db.session.commit()
    return jsonify({"status": "success", "message": "Notification marked as read"}), 200

@api_bp.route('/notifications/read-all', methods=['PUT', 'POST'])
def mark_all_notifications_read():
    """PUT /api/notifications/read-all: Marks all notifications as read."""
    user_id = session.get('user_id')
    query = Notification.query.filter_by(is_read=False)
    if user_id:
        query = query.filter((Notification.user_id == user_id) | (Notification.user_id.is_(None)))

    query.update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"status": "success", "message": "All notifications marked as read"}), 200

@api_bp.route('/notifications/<int:notif_id>', methods=['DELETE'])
def delete_notification(notif_id):
    """DELETE /api/notifications/<id>: Deletes notification."""
    notif = db.session.get(Notification, notif_id)
    if not notif:
        return jsonify({"status": "error", "message": "Notification not found"}), 404

    db.session.delete(notif)
    db.session.commit()
    return jsonify({"status": "success", "message": "Notification deleted"}), 200

# =========================================================================
# ACCOUNT DELETION (SECTION 19)
# =========================================================================

@api_bp.route('/account/delete', methods=['POST', 'DELETE'])
def delete_account():
    """Permanently removes user profile from local database and logs out."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user = db.session.get(User, user_id)
    if user:
        # Delete associated notifications
        Notification.query.filter_by(user_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()

    session.clear()
    return jsonify({"status": "success", "message": "Account deleted successfully"}), 200

# =========================================================================
# ADMIN API (SECTION 33 & 34)
# =========================================================================

@api_bp.route('/admin/users/<int:target_user_id>/role', methods=['PUT'])
def update_user_role(target_user_id):
    """Allows administrator to toggle roles between USER and ADMIN."""
    current_user_id = session.get('user_id')
    admin_user = db.session.get(User, current_user_id) if current_user_id else None

    if not admin_user or not admin_user.is_admin():
        return jsonify({"status": "error", "message": "Admin privileges required"}), 403

    target_user = db.session.get(User, target_user_id)
    if not target_user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    new_role = data.get('role', 'USER')
    if new_role in ['USER', 'ADMIN']:
        target_user.role = new_role
        db.session.commit()
        return jsonify({"status": "success", "message": f"Role updated to {new_role}"}), 200

    return jsonify({"status": "error", "message": "Invalid role specified"}), 400

