"""
SMART SOIL TESTING & CROP OPTIMIZATION SYSTEM
Automated End-to-End System Test & Verification Suite
Includes Google OAuth 2.0 Auth, Profile, Settings, Notifications, RBAC & IoT Telemetry
"""

import unittest
import json
import io
from app import create_app
from database.database import db
from database.models import User, Device, SoilReading, SystemSetting, Notification
from services.soil_analysis import SoilAnalysisService
from services.crop_optimizer import CropOptimizerService
from services.report_generator import ReportGeneratorService
from config import Config

class SmartSoilSystemTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

            # Create test admin user
            admin = User.query.filter_by(email="admin@smartsoil.local").first()
            if not admin:
                admin = User(
                    google_id="google_admin_12345",
                    email="admin@smartsoil.local",
                    name="System Administrator",
                    username="admin",
                    role="ADMIN",
                    theme_preference="light",
                    mobile_number="9876543210",
                    address="Agricultural Research Station",
                    city="Hubballi",
                    state="Karnataka",
                    country="India",
                    pincode="580020"
                )
                db.session.add(admin)

            # Create test regular user
            farmer = User.query.filter_by(email="farmer@smartsoil.local").first()
            if not farmer:
                farmer = User(
                    google_id="google_farmer_67890",
                    email="farmer@smartsoil.local",
                    name="Ramesh Patel",
                    username="ramesh",
                    role="USER",
                    theme_preference="system"
                )
                db.session.add(farmer)

            # Create test IoT device
            device = Device.query.filter_by(device_id="SOIL_001").first()
            if not device:
                device = Device(
                    device_id="SOIL_001",
                    device_name="Test Soil Sensor",
                    location="Field Plot A",
                    status="ONLINE"
                )
                db.session.add(device)

            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login_as(self, email="admin@smartsoil.local"):
        """Helper to simulate an authenticated Google user session."""
        with self.app.app_context():
            user = User.query.filter_by(email=email).first()
            with self.client.session_transaction() as sess:
                sess['user_id'] = user.id
                sess['google_id'] = user.google_id
                sess['email'] = user.email
                sess['name'] = user.get_display_name()
                sess['role'] = user.role
                sess['profile_picture'] = user.profile_picture or ""
                sess['initials'] = user.get_initials()
                sess['theme'] = user.theme_preference

    # =========================================================================
    # AUTHENTICATION & GOOGLE OAUTH TESTS
    # =========================================================================

    def test_login_page_renders_google_signin(self):
        """Verify login page renders Google Sign-In with NO password input fields."""
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Continue with Google", res.data)
        self.assertIn(b"AgriAdvisor", res.data)
        # Ensure password inputs are completely absent
        self.assertNotIn(b'type="password"', res.data)
        self.assertNotIn(b'name="password"', res.data)

    def test_google_oauth_mock_flow_and_session(self):
        """Verify the Google OAuth mock consent flow for development and automated testing."""
        # Step 1: Initiate OAuth
        init_res = self.client.get('/auth/google', follow_redirects=False)
        self.assertEqual(init_res.status_code, 302)
        self.assertIn('/auth/google/mock-consent', init_res.headers['Location'])

        # Read state token from session
        with self.client.session_transaction() as sess:
            state_token = sess.get('oauth_state')
        self.assertIsNotNone(state_token)

        # Step 2: Simulate Google OAuth callback
        callback_res = self.client.post('/auth/google/mock-callback', data={
            'state': state_token,
            'google_id': 'google_test_new_user_999',
            'email': 'newfarmer@gmail.com',
            'name': 'New Farmer',
            'picture': 'https://example.com/avatar.png'
        }, follow_redirects=False)

        self.assertEqual(callback_res.status_code, 302)

        # Verify user record was auto-created in database
        with self.app.app_context():
            new_user = User.query.filter_by(email='newfarmer@gmail.com').first()
            self.assertIsNotNone(new_user)
            self.assertEqual(new_user.google_id, 'google_test_new_user_999')
            self.assertEqual(new_user.name, 'New Farmer')
            self.assertIsNone(new_user.password_hash)  # Zero password storage

        # Verify session is populated
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('email'), 'newfarmer@gmail.com')
            self.assertEqual(sess.get('name'), 'New Farmer')

    def test_google_oauth_csrf_protection(self):
        """Verify OAuth rejects invalid state tokens to guard against CSRF."""
        res = self.client.post('/auth/google/mock-callback', data={
            'state': 'invalid_tampered_state_token',
            'email': 'attacker@gmail.com',
            'name': 'Attacker'
        }, follow_redirects=True)
        self.assertIn(b"Invalid OAuth state token", res.data)

    def test_logout(self):
        """Verify logout clears user session."""
        self.login_as("admin@smartsoil.local")
        res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertNotIn('user_id', sess)

    # =========================================================================
    # USER PROFILE & SETTINGS API TESTS
    # =========================================================================

    def test_profile_api_get_and_update(self):
        """Test GET and PUT /api/profile."""
        self.login_as("farmer@smartsoil.local")

        # GET Profile
        res = self.client.get('/api/profile')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["email"], "farmer@smartsoil.local")

        # PUT Profile Update
        update_res = self.client.put('/api/profile', json={
            "mobile_number": "9123456789",
            "address": "Plot #42, Green Valley Farm",
            "city": "Dharwad",
            "state": "Karnataka",
            "country": "India",
            "pincode": "580001"
        })
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.get_json()["status"], "success")

        # Verify database reflection
        with self.app.app_context():
            u = User.query.filter_by(email="farmer@smartsoil.local").first()
            self.assertEqual(u.mobile_number, "9123456789")
            self.assertEqual(u.city, "Dharwad")

    def test_settings_api_get_and_update(self):
        """Test GET and PUT /api/settings for appearance & notification preferences."""
        self.login_as("farmer@smartsoil.local")

        res = self.client.get('/api/settings')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("theme", data)

        # Update preferences
        put_res = self.client.put('/api/settings', json={
            "theme": "dark",
            "notifications_enabled": True,
            "email_notifications": True,
            "browser_notifications": True,
            "sensor_alerts": True,
            "soil_alerts": False
        })
        self.assertEqual(put_res.status_code, 200)
        self.assertEqual(put_res.get_json()["status"], "success")

        with self.app.app_context():
            u = User.query.filter_by(email="farmer@smartsoil.local").first()
            self.assertEqual(u.theme_preference, "dark")
            self.assertTrue(u.email_notifications)
            self.assertFalse(u.soil_alerts)

    # =========================================================================
    # NOTIFICATIONS API TESTS
    # =========================================================================

    def test_notifications_lifecycle(self):
        """Test listing, mark as read, read-all, and deletion of notifications."""
        self.login_as("farmer@smartsoil.local")

        with self.app.app_context():
            u = User.query.filter_by(email="farmer@smartsoil.local").first()
            n1 = Notification(
                user_id=u.id,
                title="Low Moisture Alert",
                message="Moisture level dropped to 18%",
                type="soil"
            )
            n2 = Notification(
                user_id=u.id,
                title="Device Offline",
                message="Sensor SOIL_001 has been disconnected",
                type="sensor"
            )
            db.session.add_all([n1, n2])
            db.session.commit()
            n1_id = n1.id

        # 1. List notifications
        list_res = self.client.get('/api/notifications')
        self.assertEqual(list_res.status_code, 200)
        data = list_res.get_json()
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["unread_count"], 2)

        # 2. Mark n1 as read
        read_res = self.client.post(f'/api/notifications/{n1_id}/read')
        self.assertEqual(read_res.status_code, 200)

        # Verify unread count decreased to 1
        list_res2 = self.client.get('/api/notifications')
        self.assertEqual(list_res2.get_json()["unread_count"], 1)

        # 3. Mark all as read
        all_read_res = self.client.post('/api/notifications/read-all')
        self.assertEqual(all_read_res.status_code, 200)
        list_res3 = self.client.get('/api/notifications')
        self.assertEqual(list_res3.get_json()["unread_count"], 0)

        # 4. Delete n1
        del_res = self.client.delete(f'/api/notifications/{n1_id}')
        self.assertEqual(del_res.status_code, 200)
        list_res4 = self.client.get('/api/notifications')
        self.assertEqual(len(list_res4.get_json()["items"]), 1)

    # =========================================================================
    # ROLE-BASED ACCESS CONTROL (RBAC) & ADMIN TESTS
    # =========================================================================

    def test_admin_route_protection(self):
        """Verify that standard USER cannot access /admin, but ADMIN can."""
        # Non-admin user
        self.login_as("farmer@smartsoil.local")
        res_user = self.client.get('/admin', follow_redirects=False)
        self.assertEqual(res_user.status_code, 302)

        # Admin user
        self.login_as("admin@smartsoil.local")
        res_admin = self.client.get('/admin', follow_redirects=False)
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"SYSTEM ADMINISTRATION CONSOLE", res_admin.data)

    def test_admin_change_role_api(self):
        """Test admin updating another user's role."""
        self.login_as("admin@smartsoil.local")

        with self.app.app_context():
            farmer = User.query.filter_by(email="farmer@smartsoil.local").first()
            farmer_id = farmer.id

        role_res = self.client.put(f'/api/admin/users/{farmer_id}/role', json={"role": "ADMIN"})
        self.assertEqual(role_res.status_code, 200)
        self.assertEqual(role_res.get_json()["status"], "success")

        with self.app.app_context():
            u = db.session.get(User, farmer_id)
            self.assertEqual(u.role, "ADMIN")

    # =========================================================================
    # ACCOUNT DELETION TESTS
    # =========================================================================

    def test_account_deletion_api(self):
        """Verify account deletion purges user record and clears session."""
        self.login_as("farmer@smartsoil.local")

        del_res = self.client.delete('/api/account/delete', json={"confirm": "DELETE"})
        self.assertEqual(del_res.status_code, 200)

        with self.app.app_context():
            user = User.query.filter_by(email="farmer@smartsoil.local").first()
            self.assertIsNone(user)

        with self.client.session_transaction() as sess:
            self.assertNotIn('user_id', sess)

    # =========================================================================
    # IOT TELEMETRY & ESP32 API TESTS
    # =========================================================================

    def test_api_soil_data_ingestion_and_validation(self):
        """Test POST /api/soil-data validation, API key auth, and storage."""
        # 1. Missing API Key
        bad_auth = self.client.post('/api/soil-data', json={
            "device_id": "SOIL_001",
            "moisture": 48.6,
            "temperature": 34.1,
            "ec": 1500,
            "ph": 6.5,
            "nitrogen": 32,
            "phosphorus": 37,
            "potassium": 48
        })
        self.assertEqual(bad_auth.status_code, 401)

        # 2. Valid Payload with Header
        valid_res = self.client.post('/api/soil-data', 
            headers={"X-API-Key": Config.API_KEY},
            json={
                "device_id": "SOIL_001",
                "moisture": 48.6,
                "temperature": 34.1,
                "ec": 1500,
                "ph": 6.5,
                "nitrogen": 32,
                "phosphorus": 37,
                "potassium": 48
            }
        )
        self.assertEqual(valid_res.status_code, 201)
        data = valid_res.get_json()
        self.assertEqual(data["status"], "success")

        # 3. Invalid payload - Malformed / Missing fields
        missing_res = self.client.post('/api/soil-data',
            headers={"X-API-Key": Config.API_KEY},
            json={
                "device_id": "SOIL_001",
                "moisture": 48.6
            }
        )
        self.assertEqual(missing_res.status_code, 400)

        # 4. Invalid payload - String / NaN in numeric field
        nan_res = self.client.post('/api/soil-data',
            headers={"X-API-Key": Config.API_KEY},
            json={
                "device_id": "SOIL_001",
                "moisture": "INVALID_NUMBER",
                "temperature": 34.1,
                "ec": 1500,
                "ph": 6.5,
                "nitrogen": 32,
                "phosphorus": 37,
                "potassium": 48
            }
        )
        self.assertEqual(nan_res.status_code, 400)

    def test_telemetry_triggers_soil_alert_notification(self):
        """Test that abnormal telemetry automatically triggers a notification."""
        # Post reading with critically low moisture (12%) and extreme acidity (4.0 pH)
        res = self.client.post('/api/soil-data',
            headers={"X-API-Key": Config.API_KEY},
            json={
                "device_id": "SOIL_001",
                "moisture": 12.0,
                "temperature": 38.0,
                "ec": 2500,
                "ph": 4.0,
                "nitrogen": 10,
                "phosphorus": 10,
                "potassium": 15
            }
        )
        self.assertEqual(res.status_code, 201)

        with self.app.app_context():
            alerts = Notification.query.filter_by(type="soil").all()
            self.assertGreater(len(alerts), 0)
            alert_titles = [a.title for a in alerts]
            self.assertTrue(any("MOISTURE" in t or "pH" in t for t in alert_titles))

    def test_latest_soil_data_api(self):
        """Test GET /api/latest-soil-data."""
        self.client.post('/api/soil-data', 
            headers={"X-API-Key": Config.API_KEY},
            json={
                "device_id": "SOIL_001",
                "moisture": 52.0,
                "temperature": 28.0,
                "ec": 1250,
                "ph": 6.8,
                "nitrogen": 45,
                "phosphorus": 35,
                "potassium": 55
            }
        )

        res = self.client.get('/api/latest-soil-data')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["device_id"], "SOIL_001")
        self.assertEqual(data["moisture"], 52.0)
        self.assertTrue(data["is_online"])
        self.assertIn("health_analysis", data)

    def test_soil_history_api(self):
        """Test GET /api/soil-history with different ranges."""
        self.client.post('/api/soil-data', 
            headers={"X-API-Key": Config.API_KEY},
            json={
                "device_id": "SOIL_001",
                "moisture": 50.0,
                "temperature": 25.0,
                "ec": 1000,
                "ph": 6.5,
                "nitrogen": 40,
                "phosphorus": 30,
                "potassium": 50
            }
        )

        res = self.client.get('/api/soil-history?range=24h')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["count"], 1)
        self.assertIn("moisture", data["series"])

    def test_crop_optimizer_service(self):
        """Test crop optimization ranking & transparent scoring."""
        sample_soil = {
            "moisture": 55.0,
            "temperature": 26.0,
            "ec": 1400.0,
            "ph": 6.5,
            "nitrogen": 45.0,
            "phosphorus": 35.0,
            "potassium": 55.0
        }
        eval_result = CropOptimizerService.evaluate_all(sample_soil)
        self.assertIn("crops", eval_result)
        self.assertGreater(len(eval_result["crops"]), 0)
        top_crop = eval_result["crops"][0]
        self.assertIn("crop_name", top_crop)
        self.assertIn("suitability_percent", top_crop)
        self.assertIn("parameters", top_crop)
        self.assertIn("ph", top_crop["parameters"])

    def test_soil_analysis_service(self):
        """Test soil health analysis and recommendations."""
        low_moisture_soil = {
            "moisture": 20.0,
            "temperature": 32.0,
            "ec": 1200.0,
            "ph": 5.2,
            "nitrogen": 20.0,
            "phosphorus": 30.0,
            "potassium": 50.0
        }
        analysis = SoilAnalysisService.evaluate_reading(low_moisture_soil)
        self.assertIn("health_index", analysis)
        self.assertIn("recommendations", analysis)
        rec_titles = [r["title"] for r in analysis["recommendations"]]
        self.assertTrue(any("Moisture" in t for t in rec_titles))
        self.assertTrue(any("Acidic" in t for t in rec_titles))

    def test_csv_export_endpoint(self):
        """Test GET /api/export/csv."""
        self.client.post('/api/soil-data', 
            headers={"X-API-Key": Config.API_KEY},
            json={
                "device_id": "SOIL_001",
                "moisture": 48.0,
                "temperature": 27.0,
                "ec": 1100,
                "ph": 6.4,
                "nitrogen": 35,
                "phosphorus": 30,
                "potassium": 45
            }
        )

        res = self.client.get('/api/export/csv')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "text/csv")
        self.assertIn(b"timestamp,device_id,moisture", res.data)

    def test_pdf_report_endpoint(self):
        """Test GET /api/export/pdf."""
        res = self.client.get('/api/export/pdf')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/pdf")
        self.assertTrue(res.data.startswith(b'%PDF'))

    def test_demo_mode_toggle_and_generation(self):
        """Test Demo Mode start/stop and simulated reading injection."""
        t_res = self.client.post('/api/demo/toggle', json={"enabled": True})
        self.assertEqual(t_res.status_code, 200)
        self.assertTrue(t_res.get_json()["demo_mode"])

        g_res = self.client.post('/api/demo/generate-reading')
        self.assertEqual(g_res.status_code, 201)
        r_data = g_res.get_json()["reading"]
        self.assertTrue(r_data["is_simulated"])

    def test_all_web_pages_load(self):
        """Verify that all authenticated frontend web routes load successfully with 200 OK."""
        self.login_as("admin@smartsoil.local")

        routes = [
            '/dashboard',
            '/live',
            '/history',
            '/crops',
            '/report',
            '/devices',
            '/test-api',
            '/esp32-setup',
            '/settings',
            '/about',
            '/profile',
            '/notifications',
            '/admin'
        ]

        for route in routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed to load! Status: {res.status_code}")

if __name__ == '__main__':
    unittest.main()
