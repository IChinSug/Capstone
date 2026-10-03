import sys
import io
import os
import json
import random
import datetime
import pandas as pd
import numpy as np

# Reconfigure stdout/stderr for UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

LOG_FILE = "auth.log"
CSV_FILE = "extracted_features.csv"

BOT_USER_AGENTS = ["python", "hydra", "curl", "nmap", "go-http", "requests", "bot", "script"]

def is_bot_user_agent(ua_str):
    if not ua_str:
        return 0
    ua_lower = str(ua_str).lower()
    return 1 if any(b in ua_lower for b in BOT_USER_AGENTS) else 0

def extract_features_from_logs(log_entries):
    """
    Calculates 6 feature vectors per log entry, including cross-entity global sliding window metrics
    to detect IP-rotating Password Spraying attacks.
    """
    rows = []
    
    for i, entry in enumerate(log_entries):
        ts_str = entry.get("timestamp")
        try:
            dt = datetime.datetime.fromisoformat(ts_str)
            now_ts = dt.timestamp()
        except Exception:
            now_ts = i * 2.0
            
        current_ip = entry.get("ip_address", "127.0.0.1")
        student_id = entry.get("student_id", "unknown")
        user_agent = entry.get("user_agent", "Mozilla/5.0")
        label = entry.get("is_attack", 0)
        
        five_min_ago = now_ts - 300
        window_logs = []
        for prev in log_entries[:i]:
            try:
                prev_dt = datetime.datetime.fromisoformat(prev["timestamp"])
                prev_ts = prev_dt.timestamp()
            except Exception:
                prev_ts = 0
            if prev_ts >= five_min_ago:
                window_logs.append({**prev, "time": prev_ts})
                
        # 1. IP-based failed attempts in 5m
        ip_failed_attempts_5m = sum(
            1 for l in window_logs 
            if l.get("ip_address") == current_ip and l.get("status") in ("FAILED", "BLOCKED")
        )
        
        # 2. Time interval since last request (sec)
        ip_logs = [l for l in window_logs if l.get("ip_address") == current_ip]
        if ip_logs:
            time_interval_sec = round(now_ts - ip_logs[-1]["time"], 2)
        else:
            time_interval_sec = 15.0
            
        # 3. IP changes for this student ID in 5m
        user_ips = set(l.get("ip_address") for l in window_logs if l.get("student_id") == student_id)
        user_ips.add(current_ip)
        ip_changes_5m = len(user_ips)
        
        # 4. Global failed attempts across ALL IPs in system in 5m (Password Spraying indicator)
        global_failed_5m = sum(1 for l in window_logs if l.get("status") in ("FAILED", "BLOCKED"))
        
        # 5. Global unique IPs with failed attempts in 5m (IP Rotation indicator)
        global_unique_ips_5m = len(set(
            l.get("ip_address") for l in window_logs if l.get("status") in ("FAILED", "BLOCKED")
        ))
        
        # 6. Automated Bot / Script User-Agent indicator
        ua_bot_flag = is_bot_user_agent(user_agent)
        
        rows.append({
            "failed_attempts_5m": ip_failed_attempts_5m,
            "time_interval_sec": time_interval_sec,
            "ip_changes_5m": ip_changes_5m,
            "global_failed_5m": global_failed_5m,
            "global_unique_ips_5m": global_unique_ips_5m,
            "ua_bot_flag": ua_bot_flag,
            "label": label
        })
        
    return pd.DataFrame(rows)

def generate_synthetic_dataset(num_samples=1500):
    """
    Generates balanced dataset for legitimate users, Account DoS attacks,
    and IP-rotating Password Spraying attacks.
    """
    np.random.seed(42)
    random.seed(42)
    rows = []
    
    # 1. Legitimate Users (~750 samples)
    for _ in range(num_samples // 2):
        rows.append({
            "failed_attempts_5m": np.random.choice([0, 1, 2], p=[0.75, 0.20, 0.05]),
            "time_interval_sec": round(float(np.random.exponential(scale=20.0) + 2.0), 2),
            "ip_changes_5m": np.random.choice([1, 2], p=[0.95, 0.05]),
            "global_failed_5m": np.random.randint(0, 3),
            "global_unique_ips_5m": np.random.randint(0, 2),
            "ua_bot_flag": 0,
            "label": 0
        })
        
    # 2. Account DoS Attacks (~375 samples)
    for _ in range(num_samples // 4):
        rows.append({
            "failed_attempts_5m": np.random.randint(5, 30),
            "time_interval_sec": round(float(np.random.uniform(0.01, 0.4)), 2),
            "ip_changes_5m": 1,
            "global_failed_5m": np.random.randint(5, 30),
            "global_unique_ips_5m": np.random.randint(1, 4),
            "ua_bot_flag": np.random.choice([0, 1], p=[0.2, 0.8]),
            "label": 1
        })
        
    # 3. IP-Rotating Password Spraying Attacks (~375 samples)
    for _ in range(num_samples // 4):
        rows.append({
            "failed_attempts_5m": np.random.choice([0, 1, 2], p=[0.7, 0.2, 0.1]),
            "time_interval_sec": round(float(np.random.uniform(0.05, 1.0)), 2),
            "ip_changes_5m": np.random.randint(3, 15),
            "global_failed_5m": np.random.randint(5, 40),
            "global_unique_ips_5m": np.random.randint(4, 30),
            "ua_bot_flag": np.random.choice([0, 1], p=[0.1, 0.9]),
            "label": 1
        })
        
    df = pd.DataFrame(rows)
    return df.sample(frac=1.0, random_state=42).reset_index(drop=True)

def main():
    print("=======================================================================")
    print(" ML 특징 추출 및 데이터셋 생성 (Feature Extraction & Dataset Generation)")
    print("=======================================================================")
    
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except Exception:
                        pass
                        
    real_df = pd.DataFrame()
    if logs:
        print(f"[+] '{LOG_FILE}' 파일에서 {len(logs)}개의 로그를 읽어 특징 벡터를 추출합니다...")
        real_df = extract_features_from_logs(logs)
        
    synth_df = generate_synthetic_dataset(1500)
    
    if not real_df.empty:
        extracted_df = pd.concat([real_df, synth_df], ignore_index=True)
    else:
        extracted_df = synth_df
        
    try:
        extracted_df.to_csv(CSV_FILE, index=False)
        print(f"[✔] 특징 벡터 데이터를 '{CSV_FILE}' 파일에 성공적으로 저장했습니다! (총 {len(extracted_df)}행)")
    except PermissionError:
        fallback_file = "extracted_features_updated.csv"
        extracted_df.to_csv(fallback_file, index=False)
        print(f"[⚠️] 알림: '{CSV_FILE}' 파일이 사용 중이므로 '{fallback_file}' 파일에 저장했습니다.")
        print(f"[💡] 안내: 열려 있는 '{CSV_FILE}' 파일을 닫고 다시 실행하세요.")


if __name__ == "__main__":
    main()
