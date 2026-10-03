import sys
import io
import requests

# Reconfigure stdout/stderr for UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

SERVER_URL = "http://127.0.0.1:5000/api/admin/unblock"

def main():
    print("=======================================================================")
    print(" 비상 IP 차단 해제 CLI 도구 (Emergency Unblock CLI Tool) ")
    print("=======================================================================")
    
    if len(sys.argv) > 1:
        target = sys.argv[1].strip()
    else:
        target = input("차단 해제할 IP 주소 또는 Username 입력 (기본값 'admin'): ").strip()
        if not target:
            target = "admin"
            
    try:
        res = requests.post(SERVER_URL, json={"target": target}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            print(f"[✔] 성공: {data.get('message')}")
            print(f"    남은 차단 목록: {data.get('remaining_blocked')}")
        else:
            print(f"[!] 오류 ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"[!] 서버 연결 실패: {e}")

if __name__ == "__main__":
    main()
