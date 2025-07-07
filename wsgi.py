import sys
import io
import threading
from app import app, check_disconnected

# Ensure print statements are immediately written to logs
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.stdout.reconfigure(line_buffering=True)
threading.Thread(target=check_disconnected, daemon=True).start()

if __name__ == "__main__":
    app.run()