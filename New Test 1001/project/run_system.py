import os
import sys
import time
import subprocess
import atexit
import socket

child_processes = []

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def cleanup_all():
    print("\n[+] 시스템의 모든 서버를 종료하고 있습니다...")
    for p in child_processes:
        try:
            p.terminate()
            p.wait(timeout=1)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    print("[✔] 모든 서버가 성공적으로 종료되었습니다.")

atexit.register(cleanup_all)

def main():
    python_exe = sys.executable
    base_dir = os.path.dirname(os.path.abspath(__file__))

    print("=======================================================================")
    print(" 🚀 SECUREAUTH 통합 시스템 실행 (SYSTEM LAUNCHER)")
    print("=======================================================================")

    # 1. Start Attacker Control Center (Port 5001)
    attacker_script = os.path.join(base_dir, "Attacker", "attacker_app.py")
    if os.path.exists(attacker_script) and not is_port_open(5001):
        print("[+] Attacker Console (Port 5001) 서버를 실행합니다...")
        p1 = subprocess.Popen([python_exe, attacker_script], cwd=base_dir)
        child_processes.append(p1)

    time.sleep(1)

    print("\n=======================================================================")
    print(" 🟢 모든 서버가 성공적으로 실행되었습니다:")
    print(" ---------------------------------------------------------------------")
    print(" 🛡️ 1. 메인 SSO 보안 서버:     http://127.0.0.1:5000")
    print(" ☠️ 2. 공격자 시뮬레이션 콘솔: http://127.0.0.1:5001")
    print("=======================================================================")
    print(" (종료하려면 Ctrl+C를 누르면 모든 서버가 함께 종료됩니다)\n")

    # 3. Start Main SSO Server in foreground
    app_script = os.path.join(base_dir, "app.py")
    try:
        p_main = subprocess.Popen([python_exe, app_script], cwd=base_dir)
        child_processes.append(p_main)
        p_main.wait()
    except KeyboardInterrupt:
        print("\n[!] Ctrl+C 입력됨.")

if __name__ == "__main__":
    main()
