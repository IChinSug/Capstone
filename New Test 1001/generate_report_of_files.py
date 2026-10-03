import os
import sys
import ast
import time
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, fill_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_cell_borders(cell, top=None, bottom=None, left=None, right=None):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}/>')
    if top:
        tcBorders.append(parse_xml(f'<w:top {nsdecls("w")} w:val="{top.get("val","single")}" w:sz="{top.get("sz","4")}" w:space="0" w:color="{top.get("color","D3D3D3")}"/>'))
    if bottom:
        tcBorders.append(parse_xml(f'<w:bottom {nsdecls("w")} w:val="{bottom.get("val","single")}" w:sz="{bottom.get("sz","4")}" w:space="0" w:color="{bottom.get("color","D3D3D3")}"/>'))
    if left:
        tcBorders.append(parse_xml(f'<w:left {nsdecls("w")} w:val="{left.get("val","single")}" w:sz="{left.get("sz","4")}" w:space="0" w:color="{left.get("color","D3D3D3")}"/>'))
    if right:
        tcBorders.append(parse_xml(f'<w:right {nsdecls("w")} w:val="{right.get("val","single")}" w:sz="{right.get("sz","4")}" w:space="0" w:color="{right.get("color","D3D3D3")}"/>'))
    tcPr.append(tcBorders)

def add_heading_styled(doc, text, level):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.bold = True
    
    if level == 1:
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(27, 54, 93)  # Navy Blue
    elif level == 2:
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(41, 128, 185) # Slate Blue
    elif level == 3:
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(52, 73, 94)  # Slate
    return p

def add_callout(doc, title, text, bg_color="F0F4F8", border_color="1B365D"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.rows[0].cells[0]
    cell.width = Inches(6.5)
    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    set_cell_borders(cell, left={"val": "single", "sz": "24", "color": border_color},
                           top={"val": "nil"}, bottom={"val": "nil"}, right={"val": "nil"})
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    r_t = p.add_run(f"📌 {title}\n")
    r_t.bold = True
    r_t.font.size = Pt(10.5)
    r_t.font.color.rgb = RGBColor(27, 54, 93)
    
    r = p.add_run(text)
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(51, 51, 51)
    
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)

def format_size(bytes_val):
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    else:
        return f"{bytes_val / (1024 * 1024):.2f} MB"

def generate_report():
    base_dir = r"c:\Users\lg\Desktop\2026- 2학기\Capstone 4\Propose\AUTH_ Anomaly_Detector\New Test 0928"
    project_dir = os.path.join(base_dir, "project")
    
    doc = Document()
    
    # Page setup - Standard 1 inch margins
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Base Normal Style
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Segoe UI'
    font.size = Pt(10.5)
    font.color.rgb = RGBColor(51, 51, 51)

    # ---------------------------------------------------------
    # COVER / TITLE SECTION
    # ---------------------------------------------------------
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(24)
    title_p.paragraph_format.space_after = Pt(8)
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title_p.add_run("AUTH_ Anomaly_Detector\nComplete Codebase & File Inventory Report")
    r.font.size = Pt(22)
    r.bold = True
    r.font.color.rgb = RGBColor(27, 54, 93)

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(20)
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = sub_p.add_run("Comprehensive File Technical Specifications, System Architecture & Code Breakdown")
    r_sub.font.size = Pt(12)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(127, 140, 141)

    # Key Metadata summary box
    meta_p = doc.add_paragraph()
    meta_p.paragraph_format.space_after = Pt(18)
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_m = meta_p.add_run("Target System: Real-Time Authentication Anomaly Detector & Attacker Simulator\n"
                         "Total Registered Project Files: 29  |  Total Code Lines: ~11,000+  |  Date: September 2026")
    r_m.font.size = Pt(9.5)
    r_m.font.color.rgb = RGBColor(52, 73, 94)

    # ---------------------------------------------------------
    # 1. EXECUTIVE OVERVIEW & DIRECTORY ARCHITECTURE
    # ---------------------------------------------------------
    add_heading_styled(doc, "1. Executive Overview & Directory Structure", level=1)
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(8)
    p.add_run(
        "This document presents a complete technical inventory and structural breakdown of all 29 files "
        "comprising the AUTH_ Anomaly_Detector project repository. The system is designed to provide real-time "
        "anomaly detection during user authentication phases, combining machine learning classifiers (Random Forest, "
        "Decision Tree, Logistic Regression, SVM), automated security responses (account suspension, IP blocking, admin rescue), "
        "a live interactive web dashboard, and an isolated live attack simulator panel."
    )

    add_callout(doc, "Project Directory Layout",
                "ROOT: c:\\Users\\lg\\Desktop\\2026- 2학기\\Capstone 4\\Propose\\AUTH_ Anomaly_Detector\\New Test 0928\n"
                "├── Call It Supporter.png                     (System Architecture Diagram / Visual Asset)\n"
                "└── project/\n"
                "    ├── app.py                               (Primary Flask Web Application & REST API Server)\n"
                "    ├── extract_features.py                  (Sliding-Window Feature Vector Extractor & Synthetic Generator)\n"
                "    ├── train_eval_models.py                 (ML Benchmark Pipeline & Model Evaluation Suite)\n"
                "    ├── generate_users.py                    (200 User Account Generator with SQLite/JSON/CSV Sync)\n"
                "    ├── generate_5000_logs.py                (Synthetic 5,000 Authentication Logs Generator)\n"
                "    ├── simulate_traffic.py                  (Multi-Threaded REST API Login Traffic Generator)\n"
                "    ├── live_attack_simulator.py             (Live HTTP Attack Execution Engine for Flask API)\n"
                "    ├── unblock_cli.py                       (CLI Tool for Unblocking Entities & Inspecting DB)\n"
                "    ├── check_db.py                          (Database Inspection & Table Diagnostic Script)\n"
                "    ├── generate_report_docx.py              (Automated Technical Summary DOCX Generator)\n"
                "    ├── README.md                            (Project Documentation & Setup Guide)\n"
                "    ├── requirements.txt                     (Python Dependencies File)\n"
                "    ├── report.docx                          (Generated Technical Report Document)\n"
                "    ├── auth.log                             (Raw Text Authentication Log File)\n"
                "    ├── users.db                             (SQLite User Database: 200 User Accounts)\n"
                "    ├── auth_logs.db                         (SQLite Log Database: Audit Trail Logs)\n"
                "    ├── users.json                           (JSON Export of User Accounts)\n"
                "    ├── users.csv                            (CSV Export of User Accounts)\n"
                "    ├── extracted_features.csv               (Dataset of 6-Feature ML Vectors)\n"
                "    ├── extracted_features_updated.csv       (Updated Dataset of 6-Feature ML Vectors)\n"
                "    ├── Attacker/\n"
                "    │   ├── attacker_app.py                  (Flask App for Attacker Panel on Port 5001)\n"
                "    │   └── templates/index.html             (Attacker Simulator Interactive UI)\n"
                "    ├── static/\n"
                "    │   ├── css/\n"
                "    │   │   ├── style.css                    (Custom Web UI Stylesheet)\n"
                "    │   │   ├── font-inter.css               (Inter Typography Definition)\n"
                "    │   │   └── font-jetbrains.css           (JetBrains Mono Font Definition)\n"
                "    │   └── js/\n"
                "    │       ├── app.js                       (Frontend Dashboard JavaScript Engine)\n"
                "    │       └── tailwind.3.4.1.js            (Standalone Offline Tailwind CSS Framework)\n"
                "    └── templates/\n"
                "        └── index.html                       (Main Security Dashboard HTML Template)")

    # ---------------------------------------------------------
    # 2. MASTER FILE CATALOG & INVENTORY TABLE
    # ---------------------------------------------------------
    add_heading_styled(doc, "2. Master File Catalog & Inventory Table", level=1)
    
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    p.add_run("The table below lists every file in the repository alongside its file size, line count, category, and core purpose.")

    file_catalog_data = [
        # (Relative Path, Category, Size, Lines, Description)
        ("Call It Supporter.png", "Asset", "66.2 KB", "N/A", "System Architecture & Workflow Diagram image asset"),
        ("project/app.py", "Core Backend", "33.5 KB", "827", "Flask REST API, Auth controller, DB init, ML classification & RBAC endpoints"),
        ("project/extract_features.py", "ML Engine", "7.1 KB", "186", "Sliding 5m window feature vector extractor (6 features) & synthetic data generator"),
        ("project/train_eval_models.py", "ML Engine", "4.6 KB", "128", "Train & benchmark 4 ML models (Random Forest 96.49% accuracy, Decision Tree, Logistic Reg, SVM)"),
        ("project/generate_users.py", "Data Script", "5.5 KB", "145", "Generates 200 student/admin accounts with bcrypt hashes, synced to SQLite/JSON/CSV"),
        ("project/generate_5000_logs.py", "Data Script", "6.5 KB", "182", "Generates 5,000 synthetic authentication audit logs for dataset creation"),
        ("project/simulate_traffic.py", "Traffic Sim", "4.9 KB", "115", "Multi-threaded REST login traffic simulator for legit users & attack scenarios"),
        ("project/live_attack_simulator.py", "Attack Sim", "16.3 KB", "372", "Live HTTP attack engine executing Brute Force, Spraying, IP Rotation & Bot attacks"),
        ("project/unblock_cli.py", "CLI Utility", "1.4 KB", "37", "CLI tool to inspect blocked IPs/Accounts and reset entity status directly in SQLite"),
        ("project/check_db.py", "CLI Utility", "0.7 KB", "20", "Diagnostic script to print record counts and sample rows from SQLite DBs"),
        ("project/generate_report_docx.py", "Report Gen", "14.0 KB", "286", "Automated script generating formatted technical Word report (report.docx)"),
        ("project/Attacker/attacker_app.py", "Attack UI App", "6.4 KB", "173", "Flask web app (Port 5001) serving live attacker control panel & API endpoints"),
        ("project/Attacker/templates/index.html", "Attack UI Template", "21.4 KB", "470", "Interactive web control panel for triggering attacks and viewing attack log streams"),
        ("project/templates/index.html", "Main UI Template", "38.2 KB", "667", "Main Security Dashboard UI template for Admin, Analyst, and Student consoles"),
        ("project/static/js/app.js", "Frontend Logic", "32.7 KB", "734", "Client-side JS handling live table pagination, API polling, tab switching & UI state"),
        ("project/static/js/tailwind.3.4.1.js", "Frontend Lib", "403.1 KB", "65", "Standalone offline compiled build of Tailwind CSS 3.4.1 UI framework"),
        ("project/static/css/style.css", "Frontend Styling", "2.5 KB", "106", "Custom styling rules, badge styles, scrollbars, and keyframe animations"),
        ("project/static/css/font-inter.css", "Frontend Font", "0.2 KB", "7", "Local CSS font face loader for Inter font family"),
        ("project/static/css/font-jetbrains.css", "Frontend Font", "0.2 KB", "7", "Local CSS font face loader for JetBrains Mono monospace code font"),
        ("project/users.db", "Database", "40.0 KB", "Binary", "SQLite database storing 200 registered users, roles, password hashes, and statuses"),
        ("project/auth_logs.db", "Database", "1.00 MB", "Binary", "SQLite database storing authentication audit trail logs and anomaly scores"),
        ("project/users.json", "Data File", "46.6 KB", "1,802", "JSON formatted export of registered student and admin account credentials"),
        ("project/users.csv", "Data File", "18.3 KB", "201", "CSV formatted export of registered student and admin account credentials"),
        ("project/extracted_features.csv", "ML Dataset", "117.3 KB", "6,556", "Extracted 6-feature dataset used for training and evaluating ML models"),
        ("project/extracted_features_updated.csv", "ML Dataset", "117.3 KB", "6,556", "Updated 6-feature ML dataset with balanced normal and anomaly samples"),
        ("project/auth.log", "Log File", "0.0 KB", "0", "Raw text file target for authentication log persistence"),
        ("project/README.md", "Documentation", "6.8 KB", "165", "Project overview, installation guide, architecture summary, and API reference"),
        ("project/requirements.txt", "Config File", "0.2 KB", "8", "List of Python dependencies (Flask, scikit-learn, pandas, numpy, python-docx, etc.)"),
        ("project/report.docx", "Document", "39.7 KB", "Binary", "Generated Microsoft Word technical project documentation report")
    ]

    table = doc.add_table(rows=len(file_catalog_data) + 1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    headers = ["File Path / Name", "Category", "Size", "Lines", "Primary Purpose"]
    col_widths = [Inches(1.8), Inches(1.1), Inches(0.7), Inches(0.6), Inches(2.3)]

    hdr_row = table.rows[0]
    for i, title in enumerate(headers):
        cell = hdr_row.cells[i]
        cell.width = col_widths[i]
        cell.text = title
        set_cell_background(cell, "1B365D")
        set_cell_margins(cell, top=120, bottom=120, left=120, right=120)
        p_hdr = cell.paragraphs[0]
        p_hdr.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p_hdr.runs[0].font.bold = True
        p_hdr.runs[0].font.size = Pt(9.5)

    for row_idx, data in enumerate(file_catalog_data, start=1):
        row_cells = table.rows[row_idx].cells
        for col_idx, text in enumerate(data):
            row_cells[col_idx].width = col_widths[col_idx]
            row_cells[col_idx].text = text
            set_cell_margins(row_cells[col_idx], top=80, bottom=80, left=100, right=100)
            p_c = row_cells[col_idx].paragraphs[0]
            p_c.runs[0].font.size = Pt(9)
            if col_idx in (2, 3):
                p_c.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            if row_idx % 2 == 0:
                set_cell_background(row_cells[col_idx], "F8F9FA")
            set_cell_borders(row_cells[col_idx], bottom={"val": "single", "sz": "4", "color": "E2E8F0"})

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ---------------------------------------------------------
    # 3. DETAILED FILE SPECIFICATIONS BY MODULE
    # ---------------------------------------------------------
    add_heading_styled(doc, "3. Core Backend & Application Engine (`project/app.py`)", level=1)
    
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "The core backend of the project resides in project/app.py (827 lines, 33.5 KB). "
        "It acts as the central command server, running a Flask WSGI application that handles incoming HTTP authentication requests, "
        "executes real-time feature extraction, evaluates machine learning predictions, enforces strict security policy controls, "
        "and serves REST API endpoints for the multi-console user interface."
    )

    add_heading_styled(doc, "Key Functions & Responsibilities in `app.py`", level=2)
    
    app_funcs = [
        ("init_db()", "Initializes the SQLite databases (users.db and auth_logs.db). Creates tables for users, logs, and blocked_entities if they do not exist, ensuring pre-populated seed data for 200 users."),
        ("train_and_load_anomaly_detector()", "Trains or loads the Random Forest Classifier using extracted_features_updated.csv. Returns the trained model, feature scaler, and dataset feature names."),
        ("extract_incoming_features(ip, student_id, user_agent)", "Computes a 6-dimensional feature vector in real time using a 300-second (5-minute) sliding window across past authentication logs stored in auth_logs.db."),
        ("classify_attack_type(features, is_bot)", "Classifies the nature of detected anomalies into specific attack categories: 'Brute Force / Account DoS', 'Single-IP Password Spraying', 'IP Rotation Spraying', or 'Automated Bot Traffic'."),
        ("login() [/login Endpoint]", "Primary endpoint handling GET (login UI) and POST (authentication attempt). Performs IP block check, account status check, credential validation, ML anomaly evaluation, automatic account suspension / IP blocking, and audit logging."),
        ("sync_users_to_json_csv()", "Ensures atomic synchronization of user account states between SQLite (users.db), JSON (users.json), and CSV (users.csv)."),
        ("update_user_status_in_db()", "Handles administrative updates to user account status. Enforces Immutable Admin Protection to prevent modifying the 'admin' account."),
        ("get_admin_logs() [/api/admin/logs]", "REST API endpoint returning paginated (10 per page), filtered audit logs for the Admin Console."),
        ("get_analyst_analytics() [/api/analyst/analytics]", "REST API endpoint providing aggregated security metrics, anomaly percentages, attack distribution charts data, and top offending IPs.")
    ]

    for f_name, f_desc in app_funcs:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        r_fn = bp.add_run(f"{f_name}: ")
        r_fn.bold = True
        r_fn.font.color.rgb = RGBColor(27, 54, 93)
        bp.add_run(f_desc)

    add_callout(doc, "Security Mechanisms Enforced by `app.py`",
                "1. Account Suspension (SUSPENDED): Triggered after 5 consecutive password failures or ML anomaly flag. Blocks target account while leaving legitimate IP active.\n"
                "2. IP Blocking (BLOCKED_ENTITIES): Triggered when Bot Agents or Spraying attacks originate from an IP. Returns HTTP 429.\n"
                "3. Admin Rescue Mode: Successful login by system admin from a blocked IP automatically clears the IP block.\n"
                "4. Immutable Admin Account: Prevents deletion or status alteration of the 'admin' superuser account.")

    # ---------------------------------------------------------
    # 4. MACHINE LEARNING & FEATURE PIPELINE
    # ---------------------------------------------------------
    add_heading_styled(doc, "4. Machine Learning & Feature Extraction Pipeline", level=1)
    
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "The machine learning subsystem consists of project/extract_features.py (186 lines, 7.1 KB) and "
        "project/train_eval_models.py (128 lines, 4.6 KB). Together, they extract sliding-window behavioral features "
        "and train high-performance classifiers."
    )

    add_heading_styled(doc, "Feature Vector Schema (6 Features)", level=2)
    
    feat_data = [
        ("failed_attempts_5m", "Numeric (Int)", "Number of authentication failures from the given IP address in the past 5 minutes (300s)."),
        ("time_interval_sec", "Numeric (Float)", "Time interval in seconds since the previous authentication request from the same IP."),
        ("ip_changes_5m", "Numeric (Int)", "Count of unique IP addresses accessing the target student account in the past 5 minutes."),
        ("global_failed_5m", "Numeric (Int)", "Total system-wide authentication failures across all accounts in the past 5 minutes."),
        ("global_unique_ips_5m", "Numeric (Int)", "Count of distinct unique IP addresses generating failures system-wide in the past 5 minutes."),
        ("ua_bot_flag", "Binary (0/1)", "1 if User-Agent string contains known bot signatures (Hydra, Python, Curl, Go, etc.), 0 otherwise.")
    ]

    tbl_f = doc.add_table(rows=len(feat_data) + 1, cols=3)
    tbl_f.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_f.autofit = False

    f_headers = ["Feature Name", "Data Type", "Description & Behavioral Context"]
    f_widths = [Inches(2.0), Inches(1.2), Inches(3.3)]

    hdr_f_cells = tbl_f.rows[0].cells
    for i, title in enumerate(f_headers):
        hdr_f_cells[i].width = f_widths[i]
        hdr_f_cells[i].text = title
        set_cell_background(hdr_f_cells[i], "2980B9")
        set_cell_margins(hdr_f_cells[i], top=100, bottom=100, left=120, right=120)
        p_c = hdr_f_cells[i].paragraphs[0]
        p_c.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p_c.runs[0].font.bold = True

    for row_idx, data in enumerate(feat_data, start=1):
        row_cells = tbl_f.rows[row_idx].cells
        for col_idx, text in enumerate(data):
            row_cells[col_idx].width = f_widths[col_idx]
            row_cells[col_idx].text = text
            set_cell_margins(row_cells[col_idx], top=80, bottom=80, left=100, right=100)
            if col_idx == 0:
                row_cells[col_idx].paragraphs[0].runs[0].font.bold = True
            if row_idx % 2 == 0:
                set_cell_background(row_cells[col_idx], "F8F9FA")

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    add_heading_styled(doc, "ML Model Benchmark & Evaluation Summary (`train_eval_models.py`)", level=2)
    
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "The evaluation script trains four machine learning classifiers on extracted_features_updated.csv "
        "using an 80/20 train/test split. Random Forest was selected as the operational engine due to its superior F1-Score (95.27%) and low false positive rate (1.07%)."
    )

    ml_bench_data = [
        ("Logistic Regression", "95.98%", "97.46%", "91.88%", "94.59%", "1.48%", "< 0.01 ms"),
        ("Decision Tree", "96.44%", "97.89%", "92.68%", "95.21%", "1.23%", "< 0.01 ms"),
        ("Random Forest (Selected Engine)", "96.49%", "98.16%", "92.54%", "95.27%", "1.07%", "0.01 ms"),
        ("Support Vector Machine (SVM)", "95.83%", "97.05%", "91.88%", "94.39%", "1.73%", "0.05 ms")
    ]

    tbl_ml = doc.add_table(rows=len(ml_bench_data) + 1, cols=7)
    tbl_ml.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_ml.autofit = False

    ml_headers = ["Model", "Accuracy", "Precision", "Recall", "F1-Score", "FPR", "Latency"]
    ml_widths = [Inches(2.1), Inches(0.7), Inches(0.7), Inches(0.7), Inches(0.7), Inches(0.7), Inches(0.9)]

    hdr_ml_cells = tbl_ml.rows[0].cells
    for i, title in enumerate(ml_headers):
        hdr_ml_cells[i].width = ml_widths[i]
        hdr_ml_cells[i].text = title
        set_cell_background(hdr_ml_cells[i], "1B365D")
        set_cell_margins(hdr_ml_cells[i], top=100, bottom=100, left=80, right=80)
        p_c = hdr_ml_cells[i].paragraphs[0]
        p_c.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p_c.runs[0].font.bold = True
        p_c.runs[0].font.size = Pt(8.5)

    for row_idx, data in enumerate(ml_bench_data, start=1):
        row_cells = tbl_ml.rows[row_idx].cells
        for col_idx, text in enumerate(data):
            row_cells[col_idx].width = ml_widths[col_idx]
            row_cells[col_idx].text = text
            set_cell_margins(row_cells[col_idx], top=60, bottom=60, left=80, right=80)
            p_c = row_cells[col_idx].paragraphs[0]
            p_c.runs[0].font.size = Pt(8.5)
            if row_idx == 3:  # Highlight Random Forest
                set_cell_background(row_cells[col_idx], "E8F8F5")
                p_c.runs[0].font.bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ---------------------------------------------------------
    # 5. DATA GENERATION & MAINTENANCE SCRIPTS
    # ---------------------------------------------------------
    add_heading_styled(doc, "5. Data Generation, Setup & Utility Scripts", level=1)
    
    data_scripts = [
        ("generate_users.py (145 lines, 5.5 KB)",
         "Generates 200 student accounts (student1 to student200) alongside admin and analyst accounts. "
         "Computes bcrypt password hashes and outputs uniform datasets across users.db, users.json, and users.csv."),
        
        ("generate_5000_logs.py (182 lines, 6.5 KB)",
         "Generates a synthetic audit trail of 5,000 authentication logs representing both legitimate traffic and attack patterns. "
         "Populates auth_logs.db with timestamps, IP addresses, failure flags, and user agents."),
        
        ("simulate_traffic.py (115 lines, 4.9 KB)",
         "A multi-threaded traffic simulator that sends HTTP POST requests to the /login endpoint. "
         "Simulates normal traffic, Account DoS attacks, and Password Spraying to test system concurrency and logging."),
        
        ("unblock_cli.py (37 lines, 1.4 KB)",
         "Command-line utility for security administrators. Allows viewing current entries in blocked_entities "
         "and suspended users, and resetting an IP address or student account status back to ACTIVE directly in SQLite."),
        
        ("check_db.py (20 lines, 0.7 KB)",
         "Quick diagnostic script that connects to users.db and auth_logs.db, counts records, and displays table schemas."),
        
        ("generate_report_docx.py (286 lines, 14.0 KB)",
         "Python script utilizing python-docx to build the project summary document report.docx.")
    ]

    for title, desc in data_scripts:
        add_heading_styled(doc, title, level=2)
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.add_run(desc)

    # ---------------------------------------------------------
    # 6. LIVE ATTACK SIMULATOR MODULE
    # ---------------------------------------------------------
    add_heading_styled(doc, "6. Live Attack Simulator Module (`project/Attacker/`)", level=1)
    
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "The Attacker module is a dedicated subsystem designed for security demonstration and red-team testing. "
        "It consists of project/Attacker/attacker_app.py (173 lines, 6.4 KB), project/Attacker/templates/index.html (470 lines, 21.4 KB), "
        "and project/live_attack_simulator.py (372 lines, 16.3 KB)."
    )

    add_heading_styled(doc, "Supported Live Attack Vectors", level=2)
    
    attack_vectors = [
        ("Brute Force / Account DoS", "Targets a selected student account with 5 rapid failed login attempts from a single IP, causing account status to flip to SUSPENDED and triggering IP block."),
        ("Single-IP Password Spraying", "Uses one IP address (198.51.100.42) to attempt a single password across multiple student accounts. Detected by ML as Password Spraying."),
        ("IP Rotation Spraying", "Rotates through random public IP addresses to attempt logins across multiple accounts, testing multi-IP anomaly correlation."),
        ("Automated Bot Traffic", "Injects HTTP requests carrying bot User-Agent strings (Hydra/v9.1, Python-urllib, Curl) to test instant UA-based bot blocking."),
        ("Continuous Traffic Loop", "Launches a continuous background background thread generating randomized legitimate and malicious traffic streams.")
    ]

    for a_name, a_desc in attack_vectors:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        r_an = bp.add_run(f"{a_name}: ")
        r_an.bold = True
        r_an.font.color.rgb = RGBColor(41, 128, 185)
        bp.add_run(a_desc)

    # ---------------------------------------------------------
    # 7. WEB FRONTEND & UI ASSETS
    # ---------------------------------------------------------
    add_heading_styled(doc, "7. Web Frontend & UI Assets (`project/templates/` & `project/static/`)", level=1)
    
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "The project includes a modern, responsive web dashboard built with HTML5, Tailwind CSS 3.4.1, and Vanilla JS. "
        "It features role-based access control (Admin, Security Analyst, Student views) and real-time log pagination."
    )

    ui_files = [
        ("project/templates/index.html (667 lines, 38.2 KB)",
         "The main single-page application (SPA) template serving the Admin Console, Security Analyst Console, and Student Dashboard. "
         "Includes tab switching, modal dialogs for adding/editing users, risk score gauge widgets, and 10-item pagination controls."),
        
        ("project/static/js/app.js (734 lines, 32.7 KB)",
         "Client-side JavaScript application logic. Handles Fetch API calls to REST endpoints (/api/admin/logs, /api/admin/stats, /api/analyst/analytics), "
         "renders dynamic table pagination, updates charts, manages user search/filtering, and handles modal interactions."),
        
        ("project/static/js/tailwind.3.4.1.js (65 lines, 403.1 KB)",
         "Offline compiled standalone build of Tailwind CSS framework 3.4.1, ensuring full styling availability without requiring external CDN internet access."),
        
        ("project/static/css/style.css (106 lines, 2.5 KB)",
         "Custom CSS enhancements including custom scrollbar styles, glowing badge indicators, status pill badges (ACTIVE, SUSPENDED, BLOCKED), and table animation keyframes."),
        
        ("project/static/css/font-inter.css & font-jetbrains.css (7 lines each)",
         "Local CSS font face loader files providing Inter and JetBrains Mono fonts for clean typography and code block formatting.")
    ]

    for f_title, f_desc in ui_files:
        add_heading_styled(doc, f_title, level=2)
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.add_run(f_desc)

    # ---------------------------------------------------------
    # 8. DATASETS, LOGS, DATABASES & STORAGE
    # ---------------------------------------------------------
    add_heading_styled(doc, "8. Databases, Data Files & Storage Formats", level=1)
    
    storage_data = [
        ("project/users.db (40.0 KB)", "SQLite Database", "Stores 200 student accounts, admin account, role definitions, password hashes, and active status."),
        ("project/auth_logs.db (1.00 MB)", "SQLite Database", "Stores historical authentication log records including timestamp, student_id, ip_address, status, user_agent, anomaly_flag, attack_type, and risk_score."),
        ("project/users.json (46.6 KB)", "JSON File", "JSON structured format of user account credentials, allowing easy inspection and API integration."),
        ("project/users.csv (18.3 KB)", "CSV File", "CSV format export of user accounts for tabular analysis."),
        ("project/extracted_features.csv (117.3 KB)", "CSV File", "6,556 rows of extracted 6-feature vectors from raw authentication logs."),
        ("project/extracted_features_updated.csv (117.3 KB)", "CSV File", "Cleaned and updated 6-feature dataset used for training the Random Forest ML classifier."),
        ("project/auth.log (0.0 KB)", "Text Log File", "Raw log target file reserved for file-system log appending."),
        ("Call It Supporter.png (66.2 KB)", "PNG Image", "Visual diagram illustration of the system workflow and supporter architecture."),
        ("project/README.md (6.8 KB)", "Markdown", "Complete project manual covering features, API specifications, installation steps, and testing guide."),
        ("project/requirements.txt (0.2 KB)", "Text File", "Python package dependencies list: Flask, scikit-learn, pandas, numpy, python-docx, etc."),
        ("project/report.docx (39.7 KB)", "Word Document", "Technical summary report document generated by generate_report_docx.py.")
    ]

    tbl_s = doc.add_table(rows=len(storage_data) + 1, cols=3)
    tbl_s.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_s.autofit = False

    s_headers = ["File Path / Name", "Storage Format", "Description & Usage"]
    s_widths = [Inches(2.2), Inches(1.3), Inches(3.0)]

    hdr_s_cells = tbl_s.rows[0].cells
    for i, title in enumerate(s_headers):
        hdr_s_cells[i].width = s_widths[i]
        hdr_s_cells[i].text = title
        set_cell_background(hdr_s_cells[i], "1B365D")
        set_cell_margins(hdr_s_cells[i], top=100, bottom=100, left=120, right=120)
        p_c = hdr_s_cells[i].paragraphs[0]
        p_c.runs[0].font.color.rgb = RGBColor(255, 255, 255)
        p_c.runs[0].font.bold = True

    for row_idx, data in enumerate(storage_data, start=1):
        row_cells = tbl_s.rows[row_idx].cells
        for col_idx, text in enumerate(data):
            row_cells[col_idx].width = s_widths[col_idx]
            row_cells[col_idx].text = text
            set_cell_margins(row_cells[col_idx], top=80, bottom=80, left=100, right=100)
            p_c = row_cells[col_idx].paragraphs[0]
            p_c.runs[0].font.size = Pt(9)
            if col_idx == 0:
                p_c.runs[0].font.bold = True
            if row_idx % 2 == 0:
                set_cell_background(row_cells[col_idx], "F8F9FA")

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ---------------------------------------------------------
    # 9. INTER-MODULE DEPENDENCY & DATA FLOW
    # ---------------------------------------------------------
    add_heading_styled(doc, "9. Inter-Module Dependency & Data Flow", level=1)
    
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.add_run(
        "The interaction flow across the project files is summarized below:\n\n"
        "1. Initialization & Seeding: generate_users.py creates 200 student records in users.db and syncs them to users.json and users.csv. "
        "generate_5000_logs.py generates initial audit logs in auth_logs.db.\n\n"
        "2. Feature Extraction & Training: extract_features.py processes logs into 6-feature vectors saved in extracted_features_updated.csv. "
        "train_eval_models.py trains the Random Forest model and outputs benchmark metrics.\n\n"
        "3. Live Application Execution: app.py starts on port 5000, loading users.db, auth_logs.db, and the Random Forest model. "
        "When authentication requests arrive at /login, extract_incoming_features() calculates real-time metrics, classifies potential anomalies, "
        "and updates user status or blocked_entities.\n\n"
        "4. Live Attack Simulation: Attacker/attacker_app.py running on port 5001 communicates with live_attack_simulator.py to launch real HTTP POST attacks "
        "against app.py's /login endpoint, demonstrating real-time detection and visualization on index.html."
    )

    # ---------------------------------------------------------
    # SAVE DOCUMENT TO BOTH LOCATIONS
    # ---------------------------------------------------------
    out1 = os.path.join(base_dir, "Reportoffiles.docx")
    out2 = os.path.join(project_dir, "Reportoffiles.docx")
    
    doc.save(out1)
    doc.save(out2)
    
    print(f"[OK] Report generated successfully at:\n  1. {out1}\n  2. {out2}")

if __name__ == "__main__":
    generate_report()
