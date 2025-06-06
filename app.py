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
            "status": "stopped",
            "connect": False,
            "ip": "",
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
        sender_ip = request.remote_addr
        print(f"Received from ESP32: {payload}, ID: {sensor_id}, IP: {sender_ip}")
        if sensor_id in machine_states.keys():
            prev_status = machine_states[sensor_id]['status']
            current_status = payload.get("status", "stopped")
            prev_update_time = machine_states[sensor_id]['update_time']
            current_time = getCurrentTime()
            # update data
            machine_states[sensor_id]['status'] = current_status
            machine_states[sensor_id]['update_time'] = current_time
            machine_states[sensor_id]['ip'] = sender_ip
            machine_states[sensor_id]['connect'] = True

            # check save database
            save_to_db(table_name, sensor_id, machine_states[sensor_id]['machine_id'], machine_states[sensor_id]['line'], current_status, current_time)

            return jsonify({"status": "ok", "message": "Data received"}), 200 
        else:
            return jsonify({"status": "error", "message": "Machine not found!"}), 404   
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": "Bad Request!"}), 400
    

def check_ping_status():
    while True:
        for sensor_id in machine_states.keys():
            ip = machine_states[sensor_id]['ip']
            if ip != "" and machine_states[sensor_id]['connect'] == True: # only check ping when connect online
                response = ping(ip, timeout=2)
                if response is None:
                    #print("ESP32 disconnect")
                    machine_states[sensor_id]['connect'] = False
                else:
                    #print("ESP32 connect")
                    machine_states[sensor_id]['connect'] = True
        time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=check_ping_status, daemon=True).start()
    app.run(host="0.0.0.0", port=5001)