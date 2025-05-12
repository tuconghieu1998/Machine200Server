import sys
from app import app

# Ensure print statements are immediately written to logs
sys.stdout.reconfigure(line_buffering=True)

if __name__ == "__main__":
    app.run()