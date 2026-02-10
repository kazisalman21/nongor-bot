
import re

LOG_FILE = "bot.log"
KEYWORDS = ["courier", "promo", "audit", "report", "export", "ERROR"]

def scan_logs():
    print(f"Scanning {LOG_FILE} for keywords: {KEYWORDS}")
    matches = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if any(k.lower() in line.lower() for k in KEYWORDS):
                    matches.append(line.strip())
        
        print(f"Found {len(matches)} matches. Showing last 50:")
        for m in matches[-50:]:
            print(m)
            
    except Exception as e:
        print(f"Error reading log: {e}")

if __name__ == "__main__":
    scan_logs()
