import sys
import io
import os
import time
import pandas as pd
import numpy as np

# Reconfigure stdout/stderr for UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
)
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

CSV_FILE = "extracted_features.csv"

def run_model_pipeline():
    print("=======================================================================")
    print(" 1. 데이터 로드 및 전처리 (Data Loading & Preprocessing)")
    print("=======================================================================")
    
    if not os.path.exists(CSV_FILE):
        print(f"[!] '{CSV_FILE}' 파일이 존재하지 않습니다. 'extract_features.py'를 먼저 실행합니다...")
        import extract_features
        extract_features.main()

    try:
        df = pd.read_csv(CSV_FILE)
    except Exception as e:
        print(f"[!] 오류: '{CSV_FILE}' 파일을 읽을 수 없습니다: {e}")
        return

    # Feature Vector (X) 및 Label (y)
    feature_cols = [
        "failed_attempts_5m", "time_interval_sec", 
        "ip_changes_5m", "global_failed_5m", "global_unique_ips_5m", "ua_bot_flag"
    ]
    
    X = df[feature_cols]
    y = df["label"]

    print(f"전체 Log 데이터 수: {len(df)}")
    print(f"  - 정상 로그인 (Label 0): {sum(y == 0)}")
    print(f"  - 이상/공격 트래픽 (Label 1): {sum(y == 1)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # Standard Scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 4개 머신러닝 모델 비교 평가
    models = {
        "Logistic Regression": (LogisticRegression(), True),
        "Decision Tree": (DecisionTreeClassifier(random_state=42), False),
        "Random Forest": (RandomForestClassifier(n_estimators=100, random_state=42), False),
        "Support Vector Machine (SVM)": (SVC(probability=True, random_state=42), True)
    }

    results = []

    print("\n=======================================================================")
    print(" 2. 머신러닝 모델 학습 및 평가 (Model Training & Evaluation)")
    print("=======================================================================")

    for name, (model, is_scaled) in models.items():
        X_tr = X_train_scaled if is_scaled else X_train
        X_te = X_test_scaled if is_scaled else X_test

        # Training Time
        t_start = time.time()
        model.fit(X_tr, y_train)
        train_time = time.time() - t_start

        # Inference Latency
        t_infer_start = time.time()
        y_pred = model.predict(X_te)
        t_infer_end = time.time()
        
        avg_latency_ms = ((t_infer_end - t_infer_start) / len(X_te)) * 1000.0

        # Performance Metrics
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        # False Positive Rate (FPR) calculation
        cm = confusion_matrix(y_test, y_pred)
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
            fpr = (fp / (fp + tn)) * 100.0 if (fp + tn) > 0 else 0.0
        else:
            fpr = 0.0

        results.append({
            "Model": name,
            "Accuracy (%)": acc * 100.0,
            "Precision (%)": prec * 100.0,
            "Recall (%)": rec * 100.0,
            "F1-Score (%)": f1 * 100.0,
            "FPR (%)": fpr,
            "Train Time (s)": train_time,
            "Latency (ms)": avg_latency_ms
        })

    # Results Table
    results_df = pd.DataFrame(results)
    
    print("\n=======================================================================")
    print(" 3. 머신러닝 모델 성능 비교 종합 결과 (Model Evaluation Results)")
    print("=======================================================================\n")
    print(results_df.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

if __name__ == "__main__":
    run_model_pipeline()