from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import create_engine, text
import os
import time
import threading

load_dotenv()

app = Flask(__name__)

app.config['SERVER'] = os.getenv('SERVER')
app.config['DATABASE'] = os.getenv('DATABASE')
app.config['DB_USERNAME'] = os.getenv('DB_USERNAME')
app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD')

# SQLAlchemy connection string
conn_str = (
    f"mssql+pyodbc://{app.config['DB_USERNAME']}:{app.config['DB_PASSWORD']}"
    f"@{app.config['SERVER']}/{app.config['DATABASE']}?driver=ODBC+Driver+17+for+SQL+Server"
)

engine = create_engine(conn_str, pool_size=5, max_overflow=2, pool_timeout=30, pool_pre_ping=True)
table_name = "ws2_working_status"

def save_to_db(sensor_id, machine_id, line, status, timestamp):
    try:
        with engine.begin() as conn:
            conn.execute(text(f"""
                INSERT INTO {table_name} (sensor_id, machine_id, line, status, timestamp)
                VALUES (:sensor_id, :machine_id, :line, :status, :timestamp)
            """), {
                "sensor_id": sensor_id,
                "machine_id": machine_id,
                "line": line,
                "status": status,
                "timestamp": timestamp
            })
        return True
    except Exception as e:
        print("Lỗi kết nối SQL Server:", e)
        return False

def getCurrentTime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def syncMachineConfig():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT sensor_id, machine_id, line, note FROM ws2_machine_config"))
            rows = result.fetchall()

        current = getCurrentTime()

        # Lưu lại các sensor_id từ DB
        db_sensor_ids = set()
        for row in rows:
            sensor_id = row.sensor_id
            db_sensor_ids.add(sensor_id)
            if sensor_id in machine_states:
                # Cập nhật các trường tĩnh nếu có thay đổi
                machine_states[sensor_id]["machine_id"] = row.machine_id
                machine_states[sensor_id]["line"] = row.line
                # Không thay đổi status, update_time, saved_time
            else:
                # Thêm mới sensor chưa có
                machine_states[sensor_id] = {
                    "sensor_id": row.sensor_id,
                    "machine_id": row.machine_id,
                    "line": row.line,
                    "status": "disconnected",
                    "ip": "",
                    "update_time": current,
                    "saved_time": ""
                }

        # Xóa các sensor_id đã bị gỡ khỏi DB
        removed = []
        for sensor_id in list(machine_states.keys()):
            if sensor_id not in db_sensor_ids:
                removed.append(sensor_id)
                del machine_states[sensor_id]
        print(f"[{current}] Synced machine config. Added/updated: {len(db_sensor_ids)}, Removed: {len(removed)} : {removed}")
        return True
    except Exception as e:
        print("Error syncing machine config:", e)
        return False

def loadMachineConfig():
    try: 
        with engine.connect() as conn:
            result = conn.execute(text("SELECT sensor_id, machine_id, line, note FROM ws2_machine_config"))
            rows = result.fetchall()

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
    except Exception as e:
        print("Load config error:", e)
        return {}

machine_states = loadMachineConfig()
print(f"LOAD CONFIG total: {len(machine_states)}")
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
    
@app.route('/machine_config')
def machine_config():
    try: 
        machines_config = loadMachineConfig()
        return jsonify({
            "machines_config": machines_config
        })
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": "Bad Request!"}), 400
    
@app.route('/sync_machine_config', methods=["PUT"])
def sync_machine_config():
    try:
        syncMachineConfig()
        return jsonify({"status": "ok", "message": "Data updated!"}), 200
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

        #print(f"Received from ESP32: {payload}, ID: {sensor_id}, IP: {sender_ip} at {current_time}")

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

@app.route('/machine_config', methods=["POST"])
def add_machine_config():
    try:
        payload = request.get_json()
        sensor_id = payload["sensor_id"]
        machine_id = payload["machine_id"]
        line = payload["line"]
        note = payload.get("note", "")

        with engine.begin() as conn:
            result = conn.execute(text("SELECT COUNT(*) AS count FROM ws2_machine_config WHERE sensor_id = :sensor_id"), {"sensor_id": sensor_id})
            if result.fetchone().count > 0:
                return jsonify({"status": "error", "message": "Sensor ID already exists"}), 400

            conn.execute(text("INSERT INTO ws2_machine_config (sensor_id, machine_id, line, note) VALUES (:sensor_id, :machine_id, :line, :note)"), {
                "sensor_id": sensor_id,
                "machine_id": machine_id,
                "line": line,
                "note": note
            })

        return jsonify({"status": "ok", "message": "Machine added"}), 201

    except Exception as e:
        print("Add error:", e)
        return jsonify({"status": "error", "message": "Bad Request!"}), 400

@app.route('/machine_config/<sensor_id>', methods=["PUT"])
def update_machine_config(sensor_id):
    try:
        payload = request.get_json()
        machine_id = payload["machine_id"]
        line = payload["line"]
        note = payload.get("note", "")

        with engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE ws2_machine_config
                SET machine_id = :machine_id, line = :line, note = :note
                WHERE sensor_id = :sensor_id
            """), {
                "machine_id": machine_id,
                "line": line,
                "note": note,
                "sensor_id": sensor_id
            })
            if result.rowcount == 0:
                return jsonify({"status": "error", "message": "Sensor ID not found"}), 404

        return jsonify({"status": "ok", "message": "Machine updated"}), 200

    except Exception as e:
        print("Update error:", e)
        return jsonify({"status": "error", "message": "Bad Request!"}), 400

@app.route('/machine_config/<sensor_id>', methods=["DELETE"])
def delete_machine_config(sensor_id):
    try:
        with engine.begin() as conn:
            result = conn.execute(text("DELETE FROM ws2_machine_config WHERE sensor_id = :sensor_id"), {"sensor_id": sensor_id})
            if result.rowcount == 0:
                return jsonify({"status": "error", "message": "Sensor ID not found"}), 404

        return jsonify({"status": "ok", "message": "Machine deleted"}), 200

    except Exception as e:
        print("Delete error:", e)
        return jsonify({"status": "error", "message": "Bad Request!"}), 400

def check_disconnected():
    while True:
        try:
            now = datetime.now()
            now_str = getCurrentTime()
            for sensor_id, state in list(machine_states.items()):
                # Bỏ qua nếu đã disconnected
                if state.get("status") == 'disconnected':
                    continue

                try:
                    last_update = datetime.strptime(state.get("update_time"), '%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    print(f"[ERROR] Invalid update_time format for {sensor_id}: {e}")
                    continue

                second_elapsed = (now - last_update).total_seconds()

                # Nếu hơn 5 phut chưa cập nhật
                if second_elapsed > 300:
                    state["status"] = 'disconnected'
                    state["update_time"] = now_str
                    save_to_db(
                        sensor_id,
                        state['machine_id'],
                        state['line'],
                        state["status"],
                        now_str
                    )
        except Exception as e:
            print(f"[ERROR] check_disconnected crashed: {e}")
        time.sleep(60)


if __name__ == "__main__":
    threading.Thread(target=check_disconnected, daemon=True).start()
    app.run(host="0.0.0.0", port=5001)