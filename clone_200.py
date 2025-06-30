import requests
import random
import time
from concurrent.futures import ThreadPoolExecutor

URL = "http://localhost:5001/sensor"  # Update to your actual server
NUM_MACHINES = 400
STATUS_OPTIONS = ["running", "stopped", "changeover"]
INTERVAL = 15  # seconds

# Generate and send a single sensor's data
def send_data(machine_id):
    payload = {
        "sensor_id": f"PZEM{machine_id:04d}",
        "status": random.choice(STATUS_OPTIONS)
    }
    try:
        response = requests.post(URL, json=payload, timeout=3)
        return f"[{payload['sensor_id']}] {response.status_code}"
    except Exception as e:
        return f"[{payload['sensor_id']}] ERROR - {e}"

# Batch send from all machines every 15 seconds
def run_scheduler():
    with ThreadPoolExecutor(max_workers=100) as executor:
        while True:
            start = time.time()
            for i in range(NUM_MACHINES):
                executor.submit(send_data, i + 1)
                time.sleep(0.037)

if __name__ == "__main__":
    run_scheduler()
