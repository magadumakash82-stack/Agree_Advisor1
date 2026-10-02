from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from .auth import login_required, admin_required, get_current_user
from database.models import Device, SoilReading, SystemSetting, User, Notification
from services.crop_optimizer import CropOptimizerService
from services.soil_analysis import SoilAnalysisService
from config import Config

web_bp = Blueprint('web', __name__)

@web_bp.context_processor
def inject_user():
    return {'current_user': get_current_user()}

@web_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('web.dashboard'))

@web_bp.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    if user and user.is_admin():
        devices = Device.query.all()
    else:
        # User sees their assigned devices, or fallback to all available
        user_devices = Device.query.filter_by(user_id=user.id).all() if user else []
        devices = user_devices if user_devices else Device.query.all()

    latest_reading = SoilReading.query.order_by(SoilReading.timestamp.desc()).first()
    return render_template(
        'dashboard.html',
        active_page='dashboard',
        devices=devices,
        latest=latest_reading,
        user=user
    )

@web_bp.route('/live')
@login_required
def live():
    devices = Device.query.all()
    return render_template(
        'live.html',
        active_page='live',
        devices=devices
    )

@web_bp.route('/history')
@login_required
def history():
    devices = Device.query.all()
    return render_template(
        'history.html',
        active_page='history',
        devices=devices
    )

@web_bp.route('/crops')
@login_required
def crops():
    latest_reading = SoilReading.query.order_by(SoilReading.timestamp.desc()).first()
    all_crops = CropOptimizerService.load_crops()
    return render_template(
        'crops.html',
        active_page='crops',
        latest=latest_reading,
        crops=all_crops
    )

@web_bp.route('/report')
@login_required
def report():
    devices = Device.query.all()
    latest_reading = SoilReading.query.order_by(SoilReading.timestamp.desc()).first()
    
    reading_data = latest_reading.to_dict() if latest_reading else {
        "device_id": "SOIL_001",
        "moisture": 48.6,
        "temperature": 28.5,
        "ec": 1400.0,
        "ph": 6.5,
        "nitrogen": 40.0,
        "phosphorus": 32.0,
        "potassium": 50.0,
        "formatted_time": "No reading recorded",
        "is_simulated": False
    }

    health_analysis = SoilAnalysisService.evaluate_reading(reading_data)
    crop_eval = CropOptimizerService.evaluate_all(reading_data)

    return render_template(
        'report.html',
        active_page='report',
        devices=devices,
        reading=reading_data,
        analysis=health_analysis,
        crop_eval=crop_eval
    )

@web_bp.route('/devices')
@login_required
def devices():
    user = get_current_user()
    if user and user.is_admin():
        devices_list = Device.query.order_by(Device.created_at.desc()).all()
    else:
        user_devices = Device.query.filter_by(user_id=user.id).order_by(Device.created_at.desc()).all() if user else []
        devices_list = user_devices if user_devices else Device.query.order_by(Device.created_at.desc()).all()

    timeout = int(SystemSetting.get_val("device_offline_timeout", Config.DEVICE_OFFLINE_TIMEOUT))
    return render_template(
        'devices.html',
        active_page='devices',
        devices=devices_list,
        timeout=timeout,
        user=user
    )

@web_bp.route('/profile')
@login_required
def profile():
    user = get_current_user()
    return render_template(
        'profile.html',
        active_page='profile',
        user=user
    )

@web_bp.route('/notifications')
@login_required
def notifications():
    user = get_current_user()
    return render_template(
        'notifications.html',
        active_page='notifications',
        user=user
    )

@web_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = get_current_user()
    if request.method == 'POST':
        api_key = request.form.get('api_key', '').strip()
        offline_timeout = request.form.get('offline_timeout', '').strip()

        if api_key:
            SystemSetting.set_val("api_key", api_key)
        if offline_timeout and offline_timeout.isdigit():
            SystemSetting.set_val("device_offline_timeout", offline_timeout)

        flash("Hardware settings saved successfully.", "success")
        return redirect(url_for('web.settings'))

    curr_api_key = SystemSetting.get_val("api_key", Config.API_KEY)
    curr_timeout = SystemSetting.get_val("device_offline_timeout", Config.DEVICE_OFFLINE_TIMEOUT)
    thresholds = SoilAnalysisService.get_thresholds()

    return render_template(
        'settings.html',
        active_page='settings',
        user=user,
        api_key=curr_api_key,
        offline_timeout=curr_timeout,
        thresholds=thresholds
    )

@web_bp.route('/admin')
@admin_required
def admin():
    total_users = User.query.count()
    active_users = User.query.filter(User.last_login.isnot(None)).count()
    total_devices = Device.query.count()
    timeout = int(SystemSetting.get_val("device_offline_timeout", Config.DEVICE_OFFLINE_TIMEOUT))
    
    devices = Device.query.all()
    online_devices = sum(1 for d in devices if d.is_online(timeout))
    total_readings = SoilReading.query.count()
    all_users = User.query.order_by(User.created_at.desc()).all()

    return render_template(
        'admin.html',
        active_page='admin',
        total_users=total_users,
        active_users=active_users,
        total_devices=total_devices,
        online_devices=online_devices,
        total_readings=total_readings,
        users=all_users,
        devices=devices,
        timeout=timeout
    )

@web_bp.route('/about')
@login_required
def about():
    return render_template(
        'about.html',
        active_page='about'
    )

@web_bp.route('/test-api')
@login_required
def test_api():
    curr_api_key = SystemSetting.get_val("api_key", Config.API_KEY)
    return render_template(
        'test_api.html',
        active_page='test_api',
        api_key=curr_api_key
    )

@web_bp.route('/esp32-setup')
@login_required
def esp32_setup():
    curr_api_key = SystemSetting.get_val("api_key", Config.API_KEY)
    return render_template(
        'esp32_setup.html',
        active_page='esp32_setup',
        api_key=curr_api_key
    )
