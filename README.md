# 🌱 AgriAdvisor: Smart Soil Testing & Crop Optimization System
### *IoT-Based Soil Monitoring, Telemetry Analytics, Agronomic Guidance & Modern Google OAuth Platform*

---

## 📌 1. Project Overview

The **AgriAdvisor System** is an end-to-end cyber-physical IoT agriculture platform designed for real-time soil health monitoring, predictive agronomic analytics, transparent crop suitability optimization, and secure user management.

A field-deployed **7-in-1 industrial soil probe** measures seven critical soil physical, chemical, and nutrient parameters:
1. **Soil Moisture** (%)
2. **Soil Temperature** (°C)
3. **Electrical Conductivity (EC)** (µS/cm)
4. **Soil pH** (pH scale)
5. **Nitrogen (N)** (mg/kg)
6. **Phosphorus (P)** (mg/kg)
7. **Potassium (K)** (mg/kg)

Data is acquired over **RS485 Modbus RTU** through a **MAX485 transceiver** to an **ESP32 microcontroller**, validated with 16-bit CRC checks, and transmitted over Wi-Fi via secure **HTTP POST** with an `X-API-Key` to a local Python **Flask REST API**. 

The web application features:
* **Google OAuth 2.0 / OpenID Connect Single Sign-On** with zero password storage.
* **Farmer Profile Management** with contact info, farm location, and onboarding.
* **Dark / Light / System Theme Modes** with persistent storage and flicker-free initialization.
* **Centralized Notification Center** with real-time threshold alert triggers, 15-minute cooldown deduplication, and optional SMTP email dispatch.
* **Role-Based Access Control (RBAC)** distinguishing standard farmers (`USER`) from system operators (`ADMIN`) with an administrative management hub.
* **Machine-to-Machine IoT Security Isolation** preserving uninterrupted telemetry via `X-API-Key`.
* **Agronomic Intelligence:** Transparent parameter-by-parameter crop suitability scoring, live soil health indexing, and downloadable **PDF Agronomic Reports** & **CSV telemetry exports**.

---

## 🏛️ 2. System Architecture

```text
+------------------------------------------------------------------------+
|                      7-IN-1 INDUSTRIAL SOIL SENSOR                     |
|           (Moisture, Temp, EC, pH, Nitrogen, Phosphorus, Potassium)     |
+------------------------------------------------------------------------+
                                   |
                                   | RS485 / Modbus RTU (Differential A & B)
                                   v
+------------------------------------------------------------------------+
|                       MAX485 TRANSCEIVER MODULE                        |
|               (Converts Differential RS485 to TTL UART)                |
+------------------------------------------------------------------------+
                                   |
                                   | UART2 (RX=GPIO16, TX=GPIO17, DE/RE=GPIO4)
                                   v
+------------------------------------------------------------------------+
|                         ESP32 WI-FI NODE                               |
|        (Modbus CRC16 Calculation, Register Parsing, JSON HTTP POST)    |
+------------------------------------------------------------------------+
                                   |
                                   | Wi-Fi 802.11 b/g/n (HTTP POST + X-API-Key)
                                   v
+------------------------------------------------------------------------+
|                         FLASK REST API BACKEND                         |
|   (/api/soil-data: Type Validation, Hardware Auth, Telemetry Alert)    |
+------------------------------------------------------------------------+
                                   |
                                   v
+------------------------------------------------------------------------+
|                          SQLITE DATABASE                               |
|         (users, devices, soil_readings, notifications, system_settings)|
+------------------------------------------------------------------------+
            |                              |                             |
            v                              v                             v
+-----------------------+      +-----------------------+     +-----------------------+
|  SOIL HEALTH ENGINE   |      |   CROP OPTIMIZATION   |     |  NOTIFICATION SERVICE |
|  & PARAMETER ADVISORY |      |   SUITABILITY ENGINE  |     |  & DEDUPLICATION / SMTP|
+-----------------------+      +-----------------------+     +-----------------------+
            |                              |                             |
            +------------------------------+-----------------------------+
                                           |
                                           v
+------------------------------------------------------------------------------------+
|                         RESPONSIVE WEB USER INTERFACE                              |
|  - Google OAuth 2.0 Login Screen                                                   |
|  - Live Dashboard & Gauges (Moisture, Temp, EC, pH, N, P, K)                       |
|  - Interactive Chart.js Telemetry Trends & Paginated Data Table                    |
|  - Parameter-by-Parameter Crop Recommendations & Agronomic Breakdown               |
|  - User Profile & Farm Details Manager                                             |
|  - Notification Center (Alert Badges, Mark as Read, Delete)                        |
|  - Multi-Tab Settings (Appearance Themes, Alert Preferences, Hardware API Keys)    |
|  - System Administration Console (User Roles, Fleet Health, KPI Counters)          |
|  - One-Click PDF Soil Health Reports & CSV Data Export                             |
+------------------------------------------------------------------------------------+
```

---

## 🔒 3. Google OAuth 2.0 / OpenID Connect Setup Guide

The application uses Google OAuth 2.0 / OpenID Connect for authentication. **Users sign in using their verified Google identity; passwords are never solicited, entered, or stored in this application.**

### A. Instant Developer Testing (Mock Mode)
The repository is pre-configured with a **Developer Mock Sign-In helper**. When `GOOGLE_CLIENT_ID` is set to `CHANGE_THIS` (the default in `.env`), clicking **"Continue with Google"** automatically routes to a developer account chooser (`/auth/google/mock-consent`). You can test immediately using preset accounts or custom email addresses without waiting for Google Cloud Console setup!

### B. Production Setup with Official Google Cloud Console
To connect to live Google accounts:

1. **Open Google Cloud Console:**
   * Go to [https://console.cloud.google.com/](https://console.cloud.google.com/).
   * Sign in with your Google / Gmail account.
   * Click **Select a project → New Project**. Name it `Smart Soil System` and click **Create**.

2. **Configure the OAuth Consent Screen:**
   * In the left sidebar, navigate to **APIs & Services → OAuth consent screen**.
   * Select **External** and click **Create**.
   * Fill in the mandatory app details:
     * **App name:** `Smart Soil Testing & Crop Optimization System`
     * **User support email:** Select your Gmail address.
     * **Developer contact information:** Enter your email address.
   * Click **Save and Continue**.
   * In the **Scopes** step, click **Add or Remove Scopes** and select:
     * `.../auth/userinfo.email`
     * `.../auth/userinfo.profile`
     * `openid`
   * Click **Save and Continue**.
   * In the **Test users** step (while in Testing status), click **Add Users** and add your Gmail address (and any tester emails).
   * Click **Save and Continue → Back to Dashboard**.

3. **Generate OAuth 2.0 Credentials:**
   * In the left sidebar, click **Credentials → Create Credentials → OAuth client ID**.
   * Select **Application type:** `Web application`.
   * **Name:** `Smart Soil Flask Client`.
   * Under **Authorized JavaScript origins**, add:
     * `http://localhost:5000`
     * `http://127.0.0.1:5000`
   * Under **Authorized redirect URIs**, add:
     * `http://localhost:5000/auth/google/callback`
     * `http://127.0.0.1:5000/auth/google/callback`
   * Click **Create**.
   * Copy the **Client ID** and **Client Secret**.

4. **Update `.env` in `smart_soil_system/`:**
   ```env
   GOOGLE_CLIENT_ID=your_actual_client_id_from_google.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_actual_client_secret_here
   GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback
   ```
5. **Restart Flask:**
   When you click **Continue with Google**, the application will seamlessly redirect to `accounts.google.com`.

---

## ⚡ 4. Hardware Requirements & Bill of Materials

| Component | Specification | Purpose |
|---|---|---|
| **7-in-1 Soil Sensor** | RS485 Modbus RTU, 9V–24V DC | Measures Moisture, Temp, EC, pH, N, P, K |
| **Microcontroller** | ESP32 Dev Module (ESP-WROOM-32) | Hardware UART, Modbus processing, Wi-Fi stack |
| **RS485 Transceiver** | MAX485 TTL to RS485 Module | Differential line conversion with DE/RE control |
| **External Power Supply** | 12V DC (1A or 2A) Adapter | Powers 7-in-1 soil probe (do not power probe from 3.3V!) |
| **Jumper Wires & Breadboard**| Male-to-Female / Male-to-Male | Circuit connections |
| **Host Computer** | Windows 10 / 11 | Runs local Flask backend, SQLite, and Web Dashboard |

---

## 🔌 5. Hardware Wiring Diagram

### Pin Connection Table

| 7-in-1 Soil Sensor Wire | MAX485 Transceiver Pin | ESP32 Dev Board | Power Supply |
|---|---|---|---|
| **VCC (Brown / Red)** | — | — | **+12V DC External Power** |
| **GND (Black)** | — | **GND** | **GND External Power (Common GND)** |
| **A (Yellow / Green)** | **A** | — | — |
| **B (Blue / White)** | **B** | — | — |
| — | **VCC** | **5V (VIN) or 3.3V** | — |
| — | **GND** | **GND** | — |
| — | **RO (Receiver Output)** | **GPIO 16 (UART2 RX)** | — |
| — | **DI (Driver Input)** | **GPIO 17 (UART2 TX)** | — |
| — | **DE & RE (Tied together)** | **GPIO 4** | — |

> ⚠️ **CRITICAL ELECTRICAL WARNINGS:**
> 1. **Common Ground:** The external 12V power supply ground **MUST** be connected to the ESP32 GND pin. Without a common ground reference, serial data will be corrupted.
> 2. **Sensor Voltage:** Most 7-in-1 soil probes require **9V to 24V DC**. Supplying 3.3V or 5V directly to the sensor will result in sensor failure or incorrect readings.

---

## 💻 6. Windows Installation & Quick Start

### Step 1: Open PowerShell
Navigate to the project directory:
```powershell
cd c:\Users\91974\OneDrive\Desktop\AKASH\FOUR_EVER\smart_soil_system
```

### Step 2: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run the Test Suite
Verify that all 20 end-to-end tests pass cleanly:
```powershell
python test_system.py
```

### Step 4: Launch the Application
```powershell
python app.py
```
*(Alternatively, simply double-click `run_soil_system.bat`).*

### Step 5: Access the Web Dashboard
* Open your browser and visit: **`http://localhost:5000`**
* Click **Continue with Google** to sign in.
* If testing locally with default settings, the interactive Developer Account Chooser lets you sign in with one click as the Administrator or a Farmer account.

---

## 👤 7. User Profile, Dark Theme & Preferences

### User Profile Management (`/profile`)
* **Google Identity Card:** Displays the user's verified Google avatar or initials, full name, verified email address, Google Subject ID, and registration timestamp.
* **Farmer Details:** Editable fields for Mobile Number, Farm Location, Address, City, State, Country, and Pincode.
* **Onboarding Modal:** When a new user logs in with Google for the first time, a non-intrusive prompt invites them to complete their agricultural profile.

### Dark / Light / System Theme Modes
* Supports three explicit theme options: **Light Theme** (clean agricultural green/white), **Dark Theme** (high-contrast deep OLED slate `#0b1120`), and **System Default** (automatically follows your OS dark/light mode preference).
* Includes a quick theme toggle (☀️ / 🌙) directly in the navigation bar.
* Features zero-flicker CSS variable initialization before DOM rendering to prevent flashing on page refresh.

### Notification Center (`/notifications`)
* Top navigation bell icon with dynamic unread counter badge.
* Displays alerts classified by type: `sensor` (hardware/offline), `soil` (thresholds: moisture, pH, EC, NPK), `crop` (compatibility updates), and `system`.
* **Smart Cooldown & Deduplication:** When sensor readings fluctuate near thresholds, the engine enforces a 15-minute cooldown to prevent notification flooding.
* **Actions:** Mark individual notification as read, Mark All as Read, or permanently delete notifications.
* **Optional SMTP Dispatch:** Configurable in `.env` to send automated email alerts when critical thresholds are crossed.

### Role-Based Access Control (RBAC) & Admin Console (`/admin`)
* **Roles:**
  * `USER`: Standard farmer account. Can view live telemetry, access crop recommendations, manage their own profile, configure preferences, and download reports.
  * `ADMIN`: System administrator. Has full access to the **System Administration Console**, including real-time KPI counters (Total Users, Devices, Telemetry Records, Unread Alerts), user directory with role promotion/demotion toggles, and device fleet monitoring.
* **Non-destructive Isolation:** The first user to register automatically becomes an `ADMIN`.

---

## 📡 8. ESP32 Arduino IDE Setup & Upload

The ESP32 firmware communicates over local Wi-Fi and connects via the Machine-to-Machine REST API. **The ESP32 uses an `X-API-Key` rather than Google OAuth, ensuring uninterrupted telemetry without web redirects or token expiry.**

1. Open **Arduino IDE** (version 2.x recommended).
2. Install the **ESP32 Board Package** (Espressif Systems).
3. Open the sketch located at:
   ```text
   smart_soil_system/esp32/smart_soil_esp32.ino
   ```
4. Find your computer's local IP address on your Wi-Fi network using PowerShell:
   ```powershell
   ipconfig
   ```
   *(Look for the IPv4 Address under your active Wi-Fi adapter, e.g. `192.168.1.100`).*
5. Update the configuration block at the top of the sketch:
   ```cpp
   const char* WIFI_SSID       = "Your_WiFi_Name";
   const char* WIFI_PASSWORD   = "Your_WiFi_Password";
   const char* SERVER_URL      = "http://192.168.1.100:5000/api/soil-data"; // Use your PC IP
   const char* API_KEY         = "CHANGE_THIS";                            // Matches Flask API key
   const char* DEVICE_ID       = "SOIL_001";
   ```
6. Select your board (**ESP32 Dev Module**) and COM port.
7. Click **Upload**, then open **Serial Monitor** at **115200 baud** to view Modbus telemetry queries and HTTP transmission logs.

---

## 📊 9. REST API Specification

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/soil-data` | Ingests 7-in-1 soil telemetry packet & triggers alerts | `X-API-Key` Header |
| `GET` | `/api/latest-soil-data` | Returns latest reading, trends, health analysis | Public / Session |
| `GET` | `/api/soil-history` | Time series for charts (`24h`, `7d`, `30d`, `custom`) | Public / Session |
| `GET` | `/api/readings-table` | Paginated records with search filter | Public / Session |
| `GET` | `/api/system-status` | Real-time status of ESP32, Wi-Fi, API, DB | Public / Session |
| `GET` | `/api/devices` | Lists registered IoT devices and online states | Public / Session |
| `POST` | `/api/devices` | Registers a new IoT hardware node | Session |
| `POST` | `/api/crops/recommendations` | Evaluates transparent crop suitability | Public / Session |
| `GET` | `/api/profile` | Fetches authenticated farmer profile | Session |
| `PUT` | `/api/profile` | Updates contact details, farm location, address | Session |
| `GET` | `/api/settings` | Fetches appearance & notification preferences | Session |
| `PUT` | `/api/settings` | Updates theme, alert toggles, and email settings | Session |
| `GET` | `/api/notifications` | Returns notification list & unread count | Session |
| `PUT/POST` | `/api/notifications/<id>/read` | Marks notification as read | Session |
| `PUT/POST` | `/api/notifications/read-all` | Marks all notifications as read | Session |
| `DELETE` | `/api/notifications/<id>` | Deletes notification record | Session |
| `POST/DELETE`| `/api/account/delete` | Permanently deletes account & notifications | Session |
| `PUT` | `/api/admin/users/<id>/role` | Updates user role (`USER` / `ADMIN`) | Admin Session |
| `POST` | `/api/demo/toggle` | Enables/disables simulated demo telemetry | Session |
| `POST` | `/api/demo/generate-reading` | Injects a realistic synthetic telemetry packet | Session |
| `GET` | `/api/export/csv` | Downloads all telemetry records as `.csv` | Public / Session |
| `GET` | `/api/export/pdf` | Generates & downloads agronomic report as `.pdf`| Public / Session |

---

## 🌾 10. Crop Suitability Engine & Transparent Scoring

The system analyzes all 7 measured parameters against configured agronomic boundaries stored in `data/crops.json`:
* **Crops Analyzed:** Rice, Wheat, Maize, Tomato, Potato, Onion, Cotton, Groundnut, Sugarcane, Chilli, Soybean, Pulses.
* **Compatibility Formula:**
  $$\text{Suitability} = \sum (\text{Parameter Score}_i \times \text{Agronomic Weight}_i)$$
  * pH Weight: 20%
  * Moisture Weight: 18%
  * EC (Salinity) Weight: 14%
  * Nitrogen (N) Weight: 14%
  * Phosphorus (P) Weight: 12%
  * Potassium (K) Weight: 12%
  * Temperature Weight: 10%
* **Transparency:** For every crop, farmers can click *"View Scoring Breakdown"* to see the exact measured value, the optimal range, and whether the factor is optimal, moderate, or limiting.
* **Disclaimer:** Recommendations are strictly indicative and based on measured soil parameters.

---

## 📁 11. Project Directory Structure

```text
smart_soil_system/
│
├── app.py                     # Main Flask application & startup entrypoint
├── config.py                  # System configuration, OAuth, thresholds & SMTP
├── requirements.txt           # Python dependencies (Flask, ReportLab, requests, etc.)
├── test_system.py             # Automated 20-test verification suite
├── .env.example               # Template environment configuration
├── .env                       # Active environment configuration
├── soil.db                    # SQLite database with non-destructive migrations
├── README.md                  # Comprehensive setup & architecture documentation
│
├── database/
│   ├── models.py              # User, Device, SoilReading, Notification, SystemSetting
│   └── database.py            # SQLite schema initialization & non-destructive migrations
│
├── routes/
│   ├── api.py                 # REST API: telemetry, profile, settings, notifications, admin
│   ├── auth.py                # Google OAuth 2.0 / OpenID Connect & Mock Consent
│   └── web.py                 # Web routes: dashboard, live, history, crops, profile, admin
│
├── services/
│   ├── soil_analysis.py       # Health index, parameter status, alerts & guidance
│   ├── crop_optimizer.py      # Transparent scoring engine for all crops
│   ├── notification_service.py# Notification manager, 15m deduplication & SMTP mailer
│   └── report_generator.py    # ReportLab PDF report generation service
│
├── data/
│   └── crops.json             # Configurable agronomic parameters for 12+ crops
│
├── templates/
│   ├── base.html              # Layout shell, theme toggle, notification bell, user dropdown
│   ├── login.html             # Split-screen Google OAuth login with security notices
│   ├── mock_google_login.html # Developer Mock Google Account Chooser
│   ├── profile.html           # Farmer profile, Google identity badge, contact details
│   ├── notifications.html     # Notification center, filter tabs, mark as read, delete
│   ├── admin.html             # System administration console, KPIs, user & fleet tables
│   ├── dashboard.html         # 7 parameter cards, status cards, crop teasers
│   ├── live.html              # High-frequency gauges, meter bars, packet log
│   ├── history.html           # Multi-series interactive Chart.js graphs & tables
│   ├── crops.html             # Crop rankings, transparent score modal & simulator
│   ├── report.html            # Printable agronomic report with PDF download
│   ├── devices.html           # Device registry, online/offline status, add modal
│   ├── settings.html          # Appearance themes, alert toggles, account deletion
│   ├── about.html             # Architecture diagram, tech stack & project info
│   ├── test_api.html          # Interactive API debugger & sensor packet injector
│   ├── esp32_setup.html       # Hardware wiring diagram, MAX485 table & tutorial
│   ├── 404.html               # Custom 404 error page
│   └── 500.html               # Custom 500 error page
│
├── static/
│   ├── css/
│   │   └── style.css          # Cohesive design system with full Light & Dark mode support
│   ├── js/
│   │   ├── dashboard.js       # Real-time polling (5s), card & badge updates
│   │   ├── charts.js          # Chart.js historical graphing & table pagination
│   │   └── crops.js           # Transparent crop scoring & simulator engine
│   └── images/
│
├── esp32/
│   └── smart_soil_esp32.ino   # Complete Arduino firmware for ESP32 + MAX485 + Modbus
│
└── reports/                   # Output folder for generated PDF reports
```

---

## 📜 12. Academic & Major Project Demonstration Notes

This project is tailored specifically for **Electronics and Communication Engineering (ECE)**, **Internet of Things (IoT)**, **Computer Science (CSE)**, and **Agricultural AI** major projects:
* Demonstrates industrial serial protocols (**RS485 Modbus RTU** with **CRC16 validation**).
* Uses hardware microcontroller UARTs and power management.
* Demonstrates modern identity protocols (**Google OAuth 2.0 / OpenID Connect**) with zero password storage.
* Implements robust hardware M2M isolation with separate API keys for IoT edge nodes.
* Features transparent, explainable agronomic scoring rather than opaque black-box recommendations.
* Implements a realistic **Demo Mode** for defense/presentation scenarios where physical soil probes cannot be brought into the seminar hall.

---

**SMART SOIL TESTING AND CROP OPTIMIZATION SYSTEM**  
*Built with Python, Flask, SQLite, ESP32, Google OAuth 2.0, and RS485 Modbus RTU.*
