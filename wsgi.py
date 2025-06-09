import sys
import threading
from app import app, check_disconnected

# Ensure print statements are immediately written to logs
sys.stdout.reconfigure(line_buffering=True)
threading.Thread(target=check_disconnected, daemon=True).start()

if __name__ == "__main__":
    app.run()