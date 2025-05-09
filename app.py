from flask import Flask, request, jsonify
import json

app = Flask(__name__)

def initMachineData():
    # Initialize 200 machines
    number_of_machines = 200
    lines = 4
    statuses = ['running', 'stopped', 'changeover']

    machine_states = {
        str(i + 1): {
            "id": i + 1,
            "status": statuses[0],
            "line": (i // (number_of_machines // lines)) + 1,
            "temperature": f"{round(20 + i % 10 + (i * 0.1), 1)}°C",
            "vibration": f"{(i * 0.01 % 3):.2f} mm/s",
            "uptime": f"{(i * 5) % 1000} hrs"
        }
        for i in range(number_of_machines)
    }
    return machine_states

machine_states = initMachineData()
# Make it accessible to machine_status

@app.route('/')
def home():
    return "WebSocket server is running and managing 200 machines."

@app.route('/machine_data')
def machine_data():
    return jsonify(machine_states)

@app.route('/sensor', methods=['POST'])
def receive_sensor_data():
    try:
        payload = request.get_json()
        machine_id = payload["id"]
        print(f"📨 Received from ESP32: {payload} DELL {machine_id}")
        if machine_id in machine_states.keys():
            machine_states[machine_id] = {
                "status": payload.get("status", "running"),
                "temperature": payload.get("temperature"),
                "vibration": payload.get("vibration"),
                "uptime": payload.get("uptime")
            }
            return jsonify({"status": "ok", "message": "Data received"}), 200 
        else:
            return jsonify({"status": "error", "message": "Machine not found!"}), 404   
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": "Bad Request!"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)