from flask import Flask, request, jsonify
import json
from dotenv import load_dotenv
import os
import pyodbc
from datetime import datetime
from ping3 import ping
import time
import threading

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
            "status": "disconnected",
            "ip": "",
            "update_time": current,
            "saved_time": ""
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
    try: 
        current_time = getCurrentTime()
        return jsonify({
            "current_time": current_time,
            "machine_states": machine_states
        })
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": "Bad Request!"}), 400
    
@app.route('/sensor', methods=['POST'])
def receive_sensor_data():
    try:
        payload = request.get_json(force=True)
        sensor_id = payload.get("sensor_id")
        current_status = payload.get("status", "stopped")
        sender_ip = request.remote_addr
        current_time = getCurrentTime()

        print(f"Received from ESP32: {payload}, ID: {sensor_id}, IP: {sender_ip} at {current_time}")

        if not sensor_id or sensor_id not in machine_states:
            return jsonify({"status": "error", "message": "Invalid or unknown sensor_id"}), 400

        # Truy xuất thông tin hiện tại của máy
        machine = machine_states[sensor_id]
        prev_status = machine['status']
        now = datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S')

        # Cập nhật thông tin tạm thời
        machine['status'] = current_status
        machine['update_time'] = current_time
        machine['ip'] = sender_ip

        # Kiểm tra điều kiện để lưu DB
        status_changed = (prev_status != current_status)
        if machine['saved_time']:
            last_saved = datetime.strptime(machine['saved_time'], '%Y-%m-%d %H:%M:%S')
            minutes_elapsed = (now - last_saved).total_seconds() / 60
        else:
            minutes_elapsed = 9999  # ép buộc lưu nếu chưa từng lưu
        if status_changed or minutes_elapsed >= 15:
            machine['saved_time'] = current_time
            save_to_db(
                table_name,
                sensor_id,
                machine['machine_id'],
                machine['line'],
                current_status,
                current_time
            )
            print(f"[{current_time}] Data saved for {sensor_id} (status: {current_status})")

        return jsonify({"status": "ok", "message": "Data received"}), 200

    except Exception as e:
        print("Error receiving sensor data:", e)
        return jsonify({"status": "error", "message": "Bad Request!"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)