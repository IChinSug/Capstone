import os
import glob

def analyze():
    files = [f for f in glob.glob("**/*", recursive=True) if os.path.isfile(f) and "__pycache__" not in f and ".git" not in f]
    for f in sorted(files):
        size = os.path.getsize(f)
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as file_handle:
                lines = len(file_handle.readlines())
        except Exception:
            lines = 0
        print(f"{f} | {size} bytes | {lines} lines")

if __name__ == "__main__":
    analyze()
