from flask import Flask, request, jsonify
import json
from dotenv import load_dotenv
import os
import pyodbc
from datetime import datetime

load_dotenv()

app = Flask(__name__)

app.config['SERVER'] = os.getenv('SERVER')
app.config['DATABASE'] = os.getenv('DATABASE')
app.config['DB_USERNAME'] = os.getenv('DB_USERNAME')
app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD')

# Cấu hình kết nối đến SQL Server
conn_str = f"DRIVER={{SQL Server}};SERVER={app.config['SERVER']};DATABASE={app.config['DATABASE']};UID={app.config['DB_USERNAME']};PWD={app.config['DB_PASSWORD']}"

table_name = "ws2_working_status"

def save_to_db(table, sensor_id, machine_id, line, status, timestamp):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        cursor.execute(f"INSERT INTO {table} (sensor_id, machine_id, line, status, timestamp) VALUES (?, ?, ?, ?, ?)",
                       (sensor_id, machine_id, line, status, timestamp))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print("Lỗi kết nối SQL Server:", e)
        return False

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

def getCurrentTime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def loadMachineConfig():
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT sensor_id, machine_id, line, note FROM ws2_machine_config")
    rows = cursor.fetchall()

    # Tạo thời gian hiện tại
    current = getCurrentTime()

    # Duyệt qua các dòng để tạo machine_states dict
    data = {
        row.sensor_id: {
            "sensor_id": row.sensor_id,
            "machine_id": row.machine_id,
            "line": row.line,
            "status": "stopped",
            "update_time": current
        }
        for i, row in enumerate(rows)
    }
    return data

machine_states = loadMachineConfig()
print(machine_states)
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
        sensor_id = payload["sensor_id"]
        print(f"📨 Received from ESP32: {payload} DELL {sensor_id}")
        if sensor_id in machine_states.keys():
            prev_status = machine_states[sensor_id]['status']
            current_status = payload.get("status", "stopped")
            prev_update_time = machine_states[sensor_id]['update_time']
            current_time = getCurrentTime()
            # update data
            machine_states[sensor_id]['status'] = current_status
            machine_states[sensor_id]['update_time'] = current_time

            # check save database
            save_to_db(table_name, sensor_id, machine_states[sensor_id]['machine_id'], machine_states[sensor_id]['line'], current_status, current_time)

            return jsonify({"status": "ok", "message": "Data received"}), 200 
        else:
            return jsonify({"status": "error", "message": "Machine not found!"}), 404   
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": "Bad Request!"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)