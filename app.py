from flask import Flask, jsonify
from socketio_instance import socketio
import machine_status  # This registers the WebSocket handlers

app = Flask(__name__)
socketio.init_app(app)

def initMachineData():
    # Initialize 200 machines
    number_of_machines = 200
    lines = 4
    statuses = ['running', 'stopped', 'maintenance']

    machine_states = {
        i + 1: {
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
from machine_status import set_machine_data_reference
set_machine_data_reference(machine_states)

@app.route('/')
def home():
    return "WebSocket server is running and managing 200 machines."

@app.route('/machine_data')
def machine_data():
    return jsonify(machine_states)

if __name__ == '__main__':
    print("Machine200Server is running at 5001")
    socketio.run(app, host='0.0.0.0', port=5001)