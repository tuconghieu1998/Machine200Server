import socketio
import random
import time
import threading

SERVER_URL = "http://localhost:5001"  # Update if different
NUMBER_OF_MACHINES = 200
SEND_INTERVAL = 5  # seconds

statuses = ['running', 'stopped', 'maintenance']

def random_machine_data(machine_id):
    return {
        "id": machine_id,
        "status": random.choice(statuses),
        "temperature": f"{random.uniform(30.0, 80.0):.1f}°C",
        "vibration": f"{random.uniform(0.1, 3.0):.2f} mm/s",
        "uptime": f"{random.randint(100, 5000)} hrs"
    }

def simulate_machine(machine_id):
    sio = socketio.Client()

    @sio.event
    def connect():
        print(f"✅ Machine {machine_id} connected")
        def send_data_loop():
            while True:
                data = random_machine_data(machine_id)
                sio.emit("sensor_data", data)
                print(f"📤 Machine {machine_id} sent data: {data}")
                time.sleep(SEND_INTERVAL)
        threading.Thread(target=send_data_loop, daemon=True).start()

    @sio.event
    def disconnect():
        print(f"🔌 Machine {machine_id} disconnected")

    @sio.on('ack')
    def on_ack(data):
        print(f"📥 Machine {machine_id} got ACK: {data}")

    try:
        sio.connect(SERVER_URL)
    except Exception as e:
        print(f"❌ Machine {machine_id} failed to connect: {e}")

# Launch all machines
for machine_id in range(1, NUMBER_OF_MACHINES + 1):
    threading.Thread(target=simulate_machine, args=(machine_id,), daemon=True).start()

# Keep the main thread alive
while True:
    time.sleep(60)
