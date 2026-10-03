import os
import sys
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def add_heading_styled(doc, text, level):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.bold = True
    
    if level == 1:
        run.font.size = Pt(18)
        run.font.color.rgb = RGBColor(27, 54, 93)  # Navy Blue
        p.paragraph_format.space_before = Pt(18)
    elif level == 2:
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(41, 128, 185) # Blue
    elif level == 3:
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(52, 73, 94)  # Slate
    return p

def create_report():
    doc = Document()

    # Page Margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Base Normal Style
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Malgun Gothic'
    font.size = Pt(11)
    font.color.rgb = RGBColor(51, 51, 51)

    # ---------------------------------------------------------
    # COVER / TITLE SECTION
    # ---------------------------------------------------------
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(36)
    title_p.paragraph_format.space_after = Pt(12)
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title_p.add_run("인증 이상 탐지 및 실시간 보안 시스템\n(AUTH_ Anomaly_Detector)")
    r.font.size = Pt(22)
    r.bold = True
    r.font.color.rgb = RGBColor(27, 54, 93)

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(36)
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = sub_p.add_run("Capstone Project Detailed Technical Report & System Documentation")
    r_sub.font.size = Pt(13)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(127, 140, 141)

    doc.add_paragraph().paragraph_format.space_after = Pt(24)

    # ---------------------------------------------------------
    # 1. EXECUTIVE SUMMARY
    # ---------------------------------------------------------
    add_heading_styled(doc, "1. 개요 (Executive Summary)", level=1)
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.add_run(
        "본 프로젝트는 기업 및 교육 기관 웹 시스템의 사용자 인증 단계(Authentication Phase)에 발생하는 "
        "사이버 공격 및 이상 트래픽(Anomaly Traffic)을 머신러닝(Machine Learning) 알고리즘과 실시간(Real-Time) "
        "보안 규칙에 기반하여 자동 탐지하고 대응(Preventive Incident Response)하는 종합 보안 시스템입니다.\n\n"
        "본 시스템은 200명의 학생 및 관리자/분석가 계정을 SQLite/JSON 데이터베이스로 관리하며, 5,000건 이상의 "
        "인증 로그 데이터로부터 6차원 특징 벡터(6-Feature Vector)를 추출하여 Random Forest, Decision Tree, "
        "Logistic Regression, SVM 모델을 통해 이상 징후를 96.49%의 높은 정확도(Accuracy)로 분류합니다."
    )

    # ---------------------------------------------------------
    # 2. SYSTEM ARCHITECTURE
    # ---------------------------------------------------------
    add_heading_styled(doc, "2. 시스템 아키텍처 및 구성 요소 (System Architecture)", level=1)

    p = doc.add_paragraph()
    p.add_run(
        "시스템 아키텍처는 Backend REST API, Machine Learning Detection Engine, Real-Time Log Pipeline, "
        "그리고 Interactive Web UI의 4개 핵심 레이어로 구성됩니다."
    )

    # Table of System Components
    table = doc.add_table(rows=5, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    headers = ["구성 레이어 (Component Layer)", "사용 기술 (Technologies)", "주요 기능 및 역할 (Core Functions)"]
    widths = [Inches(1.8), Inches(1.8), Inches(3.0)]

    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "1B365D")
        hdr_cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        hdr_cells[i].paragraphs[0].runs[0].bold = True

    comp_data = [
        ("Backend & REST API", "Python 3.13, Flask framework", "인증 요청 처리, Anomaly Filtering, RBAC API"),
        ("Database Engine", "SQLite (users.db, auth_logs.db), JSON/CSV", "200명 계정 관리, 최근 1,000건 Audit Log 저장"),
        ("Machine Learning Engine", "scikit-learn, pandas, numpy", "Random Forest 모델 (96.49% Accuracy), Feature Extraction"),
        ("Frontend Web Dashboard", "HTML5, CSS3, JavaScript (Fetch API)", "Admin, Analyst, Student 전용 3대 콘솔, 10페이지 Pagination")
    ]

    for row_idx, data in enumerate(comp_data, start=1):
        row_cells = table.rows[row_idx].cells
        for col_idx, text in enumerate(data):
            row_cells[col_idx].text = text
            set_cell_margins(row_cells[col_idx])
            if row_idx % 2 == 0:
                set_cell_background(row_cells[col_idx], "F2F4F4")

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ---------------------------------------------------------
    # 3. FEATURE EXTRACTION & ML PIPELINE
    # ---------------------------------------------------------
    add_heading_styled(doc, "3. 머신러닝 및 특징 추출 파이프라인 (ML Pipeline)", level=1)

    p = doc.add_paragraph()
    p.add_run(
        "모든 로그인 요청 시 최근 5분(300초) 슬라이딩 윈도우(Sliding Window)를 적용하여 다음 6가지 "
        "특징 벡터(Feature Vector)를 실시간으로 계산 및 추출합니다:"
    )

    feat_items = [
        ("failed_attempts_5m", "해당 IP 주소에서 최근 5분간 발생한 실패 횟수"),
        ("time_interval_sec", "해당 IP 주소의 직전 요청 간 시간 간격(초 단위)"),
        ("ip_changes_5m", "동일 계정에 최근 5분간 접근한 서로 다른 IP 주소의 수"),
        ("global_failed_5m", "전체 시스템 기준 최근 5분간 발생한 총 인증 실패 횟수"),
        ("global_unique_ips_5m", "전체 시스템 기준 인증 실패를 유발한 고유 IP 주소 수"),
        ("ua_bot_flag", "의심스러운 자동화 봇(Hydra, Python, Curl 등) 식별 바이너리 플래그 (0/1)")
    ]

    for name, desc in feat_items:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        r_b = bp.add_run(f"{name}: ")
        r_b.bold = True
        bp.add_run(desc)

    add_heading_styled(doc, "머신러닝 모델 성능 비교 평가 (Model Evaluation)", level=2)

    # ML Results Table
    ml_table = doc.add_table(rows=5, cols=7)
    ml_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    ml_headers = ["머신러닝 모델 (Model)", "Accuracy (%)", "Precision (%)", "Recall (%)", "F1-Score (%)", "FPR (%)", "Latency (ms)"]
    hdr_cells_ml = ml_table.rows[0].cells
    for i, title in enumerate(ml_headers):
        hdr_cells_ml[i].text = title
        set_cell_background(hdr_cells_ml[i], "2980B9")
        hdr_cells_ml[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        hdr_cells_ml[i].paragraphs[0].runs[0].bold = True

    ml_data = [
        ("Logistic Regression", "95.98%", "97.46%", "91.88%", "94.59%", "1.48%", "0.00 ms"),
        ("Decision Tree", "96.44%", "97.89%", "92.68%", "95.21%", "1.23%", "0.00 ms"),
        ("Random Forest (Best Model)", "96.49%", "98.16%", "92.54%", "95.27%", "1.07%", "0.01 ms"),
        ("Support Vector Machine (SVM)", "95.83%", "97.05%", "91.88%", "94.39%", "1.73%", "0.05 ms")
    ]

    for row_idx, data in enumerate(ml_data, start=1):
        row_cells = ml_table.rows[row_idx].cells
        for col_idx, text in enumerate(data):
            row_cells[col_idx].text = text
            set_cell_margins(row_cells[col_idx])
            if row_idx == 3:  # Highlight Random Forest
                set_cell_background(row_cells[col_idx], "EAFAF1")
                row_cells[col_idx].paragraphs[0].runs[0].bold = True

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ---------------------------------------------------------
    # 4. SECURITY MECHANISMS & PROTECTION LOGIC
    # ---------------------------------------------------------
    add_heading_styled(doc, "4. 보안 대응 메커니즘 및 규칙 (Security Mechanisms)", level=1)

    p = doc.add_paragraph()
    p.add_run(
        "본 시스템은 4가지 연계 보안 메커니즘을 통해 실시간 공격 차단을 수행합니다:"
    )

    sec_rules = [
        ("계정 정지 (Account Suspension - SUSPENDED)", 
         "학생 계정이 5회 연속 비밀번호 오류를 일으키거나 ML 이상 탐지에 포착되면 계정 상태가 'SUSPENDED'로 전환됩니다. "
         "학생 계정 차단 시 IP 자체는 차단되지 않으므로 정상 사용자가 다른 IP에서 잠기는 현상을 방지하며, 접근 시 HTTP 403을 반환합니다."),
        
        ("네트워크 IP 차단 (IP Blocking - BLOCKED_ENTITIES)", 
         "Bot Agent, Brute Force, Password Spraying 공격을 수행하는 의심 IP 주소를 즉시 차단 리스트에 등록하고 HTTP 429를 반환합니다."),

        ("관리자 구출 모드 (Admin Rescue Mode)", 
         "차단된 IP 주소라 하더라도 시스템 관리자(Admin)가 올바른 자격 증명으로 로그인에 성공하면 해당 IP의 차단 상태를 자동 해제하고 정상 접속 조치를 수행합니다."),

        ("관리자 계정 불변성 보호 (Immutable Admin Protection)", 
         "최고 관리자 'admin' 계정의 권한 및 상태는 변경/정지/삭제할 수 없습니다 (Read-Only / Protected Mode). "
         "웹 인터페이스 및 API 상에서 관리자 변경 시도 시 HTTP 400 에러를 반환합니다.")
    ]

    for title, desc in sec_rules:
        add_heading_styled(doc, title, level=3)
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.add_run(desc)

    # ---------------------------------------------------------
    # 5. LIVE ATTACK SIMULATION & VALIDATION
    # ---------------------------------------------------------
    add_heading_styled(doc, "5. 실시간 공격 시뮬레이션 및 검증 (Live Attack Simulation)", level=1)

    p = doc.add_paragraph()
    p.add_run(
        "live_attack_simulator.py 스크립트를 통해 http://127.0.0.1:5000/login REST API로 실제 HTTP POST 요청을 "
        "전송하여 4가지 유형의 공격을 시뮬레이션 및 검증했습니다:"
    )

    attacks = [
        ("1. Brute Force / Account DoS 공격", "단일 IP에서 특정 학생 계정으로 5회 연속 실패 요청을 전송하여 계정을 SUSPENDED로 전환하고 해당 IP를 차단했습니다."),
        ("2. Single-IP Password Spraying 공격", "단일 IP(198.51.100.42)에서 다수 학생 계정으로 공통 비밀번호 공격 시도 시 ML 모델이 'Password Spraying'으로 감지하여 IP를 차단했습니다."),
        ("3. IP Rotation Spraying 공격", "다중 IP 주소를 우회 사용하여 다수 계정을 공격할 때 'IP Rotation Spraying' 이상 징후를 정확히 감지했습니다."),
        ("4. Automated Bot Traffic / Multi-IP Anomaly", "Hydra 봇 유저에이전트 및 다중 IP 기반 자동화 공격을 완벽히 차단하고 대시보드에 기록했습니다.")
    ]

    for title, desc in attacks:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(4)
        r_b = bp.add_run(f"{title}: ")
        r_b.bold = True
        bp.add_run(desc)

    # ---------------------------------------------------------
    # 6. USER INTERFACE & AUDIT TRAIL
    # ---------------------------------------------------------
    add_heading_styled(doc, "6. 웹 사용자 인터페이스 및 감사 로그 (User Interface & Audit Trail)", level=1)

    p = doc.add_paragraph()
    p.add_run(
        "웹 시스템(http://127.0.0.1:5000)은 3가지 사용자 역할별 콘솔을 제공합니다:\n"
        "1. Admin Console: 사용자 상태(Active / Suspended) 변경, IP 차단 해제, 10페이지 1,000건 Audit Log 테이블 제공\n"
        "2. Analyst Console: 시스템 보안 로그 분석 및 Anomaly Statistics 대시보드 제공\n"
        "3. Student Dashboard: 학생 본인의 로그인 이력, 접속 IP 및 Risk Score 확인 가능"
    )

    # ---------------------------------------------------------
    # 7. CONCLUSION & RECOMMENDATIONS
    # ---------------------------------------------------------
    add_heading_styled(doc, "7. 결론 및 향후 발전 방향 (Conclusion & Future Work)", level=1)

    p = doc.add_paragraph()
    p.add_run(
        "본 AUTH_ Anomaly_Detector 시스템은 웹 로그인 단계의 이상 트래픽을 머신러닝으로 96.49%의 높은 정확도로 "
        "탐지하고 IP 차단 및 계정 정지를 실시간으로 제어할 수 있음을 검증했습니다.\n\n"
        "향후 2-Factor Authentication (2FA/OTP) 및 외부 Threat Intelligence (Geo-IP) 연동을 통해 보안성을 "
        "한층 강화할 예정입니다."
    )

    output_path = "report.docx"
    doc.save(output_path)
    print(f"[OK] Report generated successfully: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    create_report()
