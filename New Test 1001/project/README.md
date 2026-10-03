# 🛡️ SecureAuth: Authentication Anomaly Detector & Live Attack Simulator

> **Capstone Project**: Real-Time ML-Based Authentication Anomaly Detection System with Dynamic Attack Simulation Console, 2FA Email OTP Account Recovery, and Cryptographic Password Hashing.

---

## 📋 Overview

**SecureAuth Anomaly Detector** is an intelligent Single Sign-On (SSO) security platform designed to detect, classify, and mitigate malicious authentication patterns in real time. Powered by a **Random Forest Machine Learning Engine** and a **6-Dimensional Feature Extraction Pipeline**, the system continuously monitors authentication attempts, calculates dynamic **Risk Scores (%)**, and applies inline security actions (such as IP lockout and account suspension).

The project includes an **Attacker Control Center & Live Simulator**, enabling security analysts to simulate real-time cyber attacks against the SSO server across a benchmark database of 200 student accounts.

---

## ✨ Key Features & Security Architecture

- **🔑 Cryptographic Salted Password Hashing (`scrypt` / `PBKDF2`)**:
  - Implements Werkzeug `generate_password_hash` and `check_password_hash` across all user database records (`users.db`, `users.json`, `users.csv`).
  - Passwords stored in salted hash format (e.g. `scrypt:32768:8:1$...`), preventing rainbow table and brute-force data breach decryption.

- **✨ Real-Time Visual Password Policy UI Feedback**:
  - Enforces 5-point password strength rules: (1) 8+ characters, (2) uppercase `A-Z`, (3) lowercase `a-z`, (4) digit `0-9`, (5) special character `!@#$%^&*`.
  - Interactive visual checklist (`#passwordRulesBox`) dynamically updates rule status (`✓` green / `✕` gray) as the user types. Password submission button remains disabled until all 5 rules pass.

- **📧 2FA Email OTP Account Recovery Engine**:
  - Suspended (`SUSPENDED`) accounts automatically route to 2FA Email verification.
  - Verifies Student ID and registered Email match before issuing a 5-minute valid 6-digit OTP code.
  - **Attacker Isolation Rule**: Blocked attacker IPs cannot request 2FA OTP codes for victim accounts.

- **⚡ Sliding Window Rate Limiting (DoS / Flooding Protection)**:
  - In-memory `RateLimiter` sliding window class protects sensitive endpoints:
    - `POST /login`: Max 15 requests per minute per IP (Returns `HTTP 429 Too Many Requests`).
    - `POST /api/user/2fa/request-otp`: Max 5 requests per minute per IP.

- **🛡️ Production Security & Cookie Hardening**:
  - Configured with `python-dotenv` loading from `.env` (Secret key, environment flags).
  - Session cookie flags set: `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, and 30-minute session expiration.

- **✉️ Real SMTP Email Dispatcher**:
  - Integrated `send_real_email_otp()` helper function with TLS/SSL SMTP server support (Gmail, AWS SES, SendGrid). Seamless fallback to console log when SMTP environment credentials are absent.

- **🧠 Real-Time 6D Feature Extraction Pipeline**:
  Extracts temporal and behavioral feature vectors for every incoming request:
  1. `failed_attempts_5m` (Recent IP failure frequency within 5 mins)
  2. `time_interval_sec` (Time gap between requests from the same IP)
  3. `ip_changes_5m` (Unique IP count attempting the same user account)
  4. `global_failed_5m` (Total system-wide authentication failures)
  5. `global_unique_ips_5m` (Total unique IPs causing failures)
  6. `ua_bot_flag` (Bot/Script User-Agent indicator)

- **🎯 Machine Learning Anomaly Detection & Dynamic Risk Scoring**:
  - Uses a trained **Random Forest Classifier** to compute dynamic probabilistic Risk Scores (`0.0%` to `100.0%`).
  - Automatically classifies detected anomalies into 4 distinct attack categories:
    - ⚡ **Brute Force / Account DoS**
    - 🔑 **Single-IP Password Spraying**
    - 🌐 **IP Rotation Password Spraying**
    - 🤖 **Automated Bot Traffic**

- **🔒 Inline Security & Admin Rescue Mode**:
  - **IP Lockout (HTTP 429)** and **Account Suspension (HTTP 403)** triggered on threat threshold breach.
  - **Admin Rescue Mode**: Admin login automatically unblocks an IP if authenticated with correct credentials.

- **☠️ Attacker Control Panel & Attack Simulator**:
  - Interactive Web GUI ([http://127.0.0.1:5001](http://127.0.0.1:5001)) to launch targeted or random attack vectors.
  - Dynamic random victim sampling across 200 pre-generated student accounts (`users.db`).
  - Real-time continuous background traffic generator mixing legitimate user logins with attack bursts.

---

## 📁 Directory Structure

```
project/
├── app.py                      # Main SSO Server, ML Engine, 2FA OTP & Rate Limiter (Port 5000)
├── live_attack_simulator.py    # Modular Attack Vector Simulator & Traffic Loop
├── Attacker/
│   ├── attacker_app.py         # Attacker Web Control Center Server (Port 5001)
│   └── templates/
│       └── index.html          # Attacker Web Console GUI Dashboard
├── generate_users.py           # 200 Student Accounts Generator with Salted Hashes (users.db / users.json)
├── generate_updated_report_docx.py # Automated Updated Word Report Generator
├── extract_features.py         # Feature Extraction & Dataset Pipeline
├── train_eval_models.py        # ML Model Training & Evaluation Script
├── unblock_cli.py              # CLI tool for IP unblocking & management
├── .env                        # Production Security Environment Variables
├── .env.example                # Production Environment Template
├── auth_logs.db                # Target SSO Server Security Event Database (SQLite)
├── attacker_logs.db            # Attacker Console Event Database (SQLite)
├── users.db                    # User Directory Database (200 Student Accounts, Salted Hashes)
├── report_updated.docx         # Comprehensive Technical Report (Word Format)
├── requirements.txt            # Python Dependencies Manifest
└── README.md                   # Project Documentation
```

---

## ⚙️ Installation & Prerequisites

### Prerequisites
- **Python**: `3.10` or higher
- **OS**: Windows, macOS, or Linux

### 1. Clone or Open Project Directory
```bash
cd "AUTH_ Anomaly_Detector/New Test 1001/project"
```

### 2. Install Required Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Quick Start Guide

### Step 1: Initialize User Directory & Environment (.env)
Generate the 200 student accounts with salted password hashes in `users.db`:
```bash
python generate_users.py
```

### Step 2: Launch Main SSO Server
Start the SSO Authentication Server with built-in ML Anomaly Detector & 2FA Recovery:
```bash
python app.py
```
> SSO Server runs at: **`http://127.0.0.1:5000`**

### Step 3: Launch Attacker Control Panel (Web UI)
In a separate terminal window, launch the Attacker Web Interface:
```bash
python Attacker/attacker_app.py
```
> Attacker Console runs at: **`http://127.0.0.1:5001`**

Open **`http://127.0.0.1:5001`** in your browser to launch attack vectors or start real-time continuous background traffic.

---

## 💻 CLI Attack Simulator Options

You can also run the simulator directly from the command line:

- **Idle / Manual Mode (Default)**:
  ```bash
  python live_attack_simulator.py
  ```
- **Single Test Suite Execution (Runs 4 attack types once)**:
  ```bash
  python live_attack_simulator.py --test
  ```
- **Continuous Traffic Generator (Infinite Loop)**:
  ```bash
  python live_attack_simulator.py --loop
  ```

---

## 🌐 API Routes Reference

### Main SSO Server (`http://127.0.0.1:5000`)
- `POST /login` - Main SSO authentication & rate-limited endpoint (Extracts features, evaluates ML model, logs events).
- `POST /api/user/2fa/request-otp` - Requests 6-digit 2FA OTP code for matching student ID + registered email.
- `POST /api/user/2fa/verify-unsuspend` - Verifies OTP code, validates password strength, updates password hash, & restores account to ACTIVE.
- `GET /api/analyst/analytics` - Security Analyst dashboard analytics feed.
- `GET /api/user/logs?student_id=<id>` - User-specific login history logs.

### Attacker Server (`http://127.0.0.1:5001`)
- `POST /api/attack/brute_force` - Triggers Brute Force / Account DoS attack.
- `POST /api/attack/password_spraying` - Triggers Single-IP Password Spraying attack.
- `POST /api/attack/ip_rotation` - Triggers IP Rotation Password Spraying attack.
- `POST /api/attack/bot_traffic` - Triggers Automated Bot Traffic attack.
- `POST /api/attack/continuous/start` - Starts continuous real-time background loop.
- `POST /api/attack/continuous/stop` - Stops continuous background loop.
- `POST /api/attack/logs/clear` - Clears Attacker Terminal Console & `attacker_logs.db`.

---

## 📦 Main Dependencies (`requirements.txt`)

| Package | Version | Purpose |
| :--- | :--- | :--- |
| **Flask** | `3.1.2` | Web Framework for SSO Server & Attacker App |
| **pandas** | `3.0.2` | Dataframe Processing & Feature Extraction |
| **numpy** | `2.2.6` | Numerical Operations for ML Vectors |
| **scikit-learn** | `1.8.0` | Random Forest ML Engine & Evaluation Metrics |
| **python-dotenv** | `1.0.1` | Load Production Environment Variables from `.env` |
| **requests** | `2.32.4` | Real HTTP Traffic Generator & Attack Payload Sender |
| **python-docx** | `1.2.0` | Automated Analytical Report Generation |
| **matplotlib** | `3.10.8` | Data Visualization & Confusion Matrix Rendering |

---

## 📄 License
Academic Capstone Project & Educational Security Research.
