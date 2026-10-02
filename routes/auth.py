import os
import secrets
import urllib.parse
from datetime import datetime, timezone
from functools import wraps
import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from database.database import db
from database.models import User
from config import Config

auth_bp = Blueprint('auth', __name__)

# Google OAuth 2.0 / OpenID Connect Endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

def get_current_user():
    """Retrieves the currently authenticated user from session."""
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in with your Google account to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in with your Google account to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        user = get_current_user()
        if not user or not user.is_admin():
            flash("Unauthorized: Administrator privileges are required to access this resource.", "danger")
            return redirect(url_for('web.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def is_google_configured():
    client_id = Config.GOOGLE_CLIENT_ID
    client_secret = Config.GOOGLE_CLIENT_SECRET
    return bool(client_id and client_id != "CHANGE_THIS" and client_secret and client_secret != "CHANGE_THIS")

@auth_bp.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('web.dashboard'))
    
    return render_template(
        'login.html',
        is_google_configured=is_google_configured()
    )

@auth_bp.route('/auth/google')
def google_auth():
    """Initiates Google OAuth 2.0 Authorization Code Flow."""
    # Generate CSRF state token
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    next_url = request.args.get('next')
    if next_url:
        session['oauth_next'] = next_url

    if not is_google_configured():
        # Fallback to local Developer Google Sign-In helper so testing works immediately
        return redirect(url_for('auth.mock_google_consent', state=state))

    # Real Google OAuth 2.0 authorization redirect
    params = {
        'client_id': Config.GOOGLE_CLIENT_ID,
        'redirect_uri': Config.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account'
    }
    google_redirect = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(google_redirect)

@auth_bp.route('/auth/google/callback')
def google_callback():
    """Handles Google OAuth 2.0 callback and token exchange."""
    error = request.args.get('error')
    if error:
        flash(f"Google sign-in was canceled or encountered an error: {error}", "danger")
        return redirect(url_for('auth.login'))

    code = request.args.get('code')
    state = request.args.get('state')

    # Verify state against CSRF
    expected_state = session.pop('oauth_state', None)
    if not state or state != expected_state:
        flash("Invalid OAuth state token. Possible CSRF detected.", "danger")
        return redirect(url_for('auth.login'))

    if not code:
        flash("Missing authorization code from Google.", "danger")
        return redirect(url_for('auth.login'))

    try:
        # Exchange code for token
        token_data = {
            'code': code,
            'client_id': Config.GOOGLE_CLIENT_ID,
            'client_secret': Config.GOOGLE_CLIENT_SECRET,
            'redirect_uri': Config.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        token_resp = requests.post(GOOGLE_TOKEN_URL, data=token_data, timeout=10)
        token_json = token_resp.json()

        if token_resp.status_code != 200:
            flash(f"Failed to exchange Google token: {token_json.get('error_description', 'Error')}", "danger")
            return redirect(url_for('auth.login'))

        access_token = token_json.get('access_token')

        # Retrieve user profile from Google UserInfo endpoint
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_resp = requests.get(GOOGLE_USERINFO_URL, headers=headers, timeout=10)
        userinfo = userinfo_resp.json()

        if userinfo_resp.status_code != 200:
            flash("Failed to retrieve profile information from Google.", "danger")
            return redirect(url_for('auth.login'))

        google_id = userinfo.get('sub')
        email = userinfo.get('email')
        name = userinfo.get('name')
        picture = userinfo.get('picture')

        return complete_google_login(google_id, email, name, picture)

    except Exception as e:
        flash(f"Google authentication error: {str(e)}", "danger")
        return redirect(url_for('auth.login'))

@auth_bp.route('/auth/google/mock-consent')
def mock_google_consent():
    """Developer Mock Google Account selector when real Google Cloud keys are not yet configured."""
    state = request.args.get('state')
    return render_template('mock_google_login.html', state=state)

@auth_bp.route('/auth/google/mock-callback', methods=['POST'])
def mock_google_callback():
    """Processes simulated Google login for seamless local development testing."""
    state = request.form.get('state')
    expected_state = session.pop('oauth_state', None)
    if not state or state != expected_state:
        flash("Invalid OAuth state token.", "danger")
        return redirect(url_for('auth.login'))

    google_id = request.form.get('google_id', 'google_dev_108293847291')
    email = request.form.get('email', 'rkpujari@gmail.com').strip()
    name = request.form.get('name', 'Rakesh Pujari').strip()
    picture = request.form.get('picture', '')

    return complete_google_login(google_id, email, name, picture)

def complete_google_login(google_id, email, name, picture):
    """Common login/registration logic for verified Google accounts."""
    if not email:
        flash("Google did not provide a verified email address.", "danger")
        return redirect(url_for('auth.login'))

    now = datetime.now(timezone.utc)

    # 1. Look up user by google_id or email
    user = User.query.filter((User.google_id == google_id) | (User.email == email)).first()

    is_first_user = User.query.count() == 0

    if not user:
        # Create new user automatically
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            profile_picture=picture,
            role="ADMIN" if is_first_user else "USER",
            created_at=now,
            last_login=now
        )
        db.session.add(user)
        is_new_user = True
    else:
        # Update existing user profile with latest Google data
        if not user.google_id:
            user.google_id = google_id
        if name and not user.name:
            user.name = name
        if picture:
            user.profile_picture = picture
        user.last_login = now
        is_new_user = False

    db.session.commit()

    # Create application session
    session.clear()
    session['user_id'] = user.id
    session['google_id'] = user.google_id
    session['email'] = user.email
    session['name'] = user.get_display_name()
    session['role'] = user.role
    session['profile_picture'] = user.profile_picture or ""
    session['initials'] = user.get_initials()
    session['theme'] = user.theme_preference

    # Check if onboarding prompt should be displayed
    if not user.mobile_number or not user.address:
        session['show_onboarding'] = True

    flash(f"Welcome back, {user.get_display_name()}! Signed in securely with Google.", "success")

    next_url = session.pop('oauth_next', None)
    return redirect(next_url or url_for('web.dashboard'))

@auth_bp.route('/logout')
def logout():
    """Securely logs the user out, clears session, and redirects to login."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))

def ensure_default_user():
    """Seeds a default developer/admin account if no users exist in the database."""
    if User.query.count() == 0:
        default_admin = User(
            google_id="google_dev_admin_001",
            email="admin@smartsoil.local",
            name="System Administrator",
            username="admin",
            role="ADMIN",
            theme_preference="system"
        )
        db.session.add(default_admin)
        db.session.commit()

