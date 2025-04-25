from flask import request
from socketio_instance import socketio

connected_clients = set()
machine_data = None  # Will be set by app.py

def set_machine_data_reference(ref):
    global machine_data
    machine_data = ref

@socketio.on('connect')
def on_connect():
    sid = request.sid
    connected_clients.add(sid)
    print(f"🟢 Connected: {sid} | Total: {len(connected_clients)}")

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    connected_clients.discard(sid)
    print(f"🔴 Disconnected: {sid} | Total: {len(connected_clients)}")

@socketio.on('sensor_data')
def handle_sensor_data(data):
    sid = request.sid
    machine_id = data.get("id")

    if machine_id in machine_data:
        machine_data[machine_id].update({
            "status": data.get("status", "running"),
            "temperature": data.get("temperature"),
            "vibration": data.get("vibration"),
            "uptime": data.get("uptime")
        })
        print(f"✅ Updated machine #{machine_id} from {sid}: {machine_data[machine_id]}")
        
        # Optional: Emit update to a dashboard room or admin client
        # socketio.emit("machine_update", { "id": machine_id, "data": machine_data[machine_id] })

        socketio.emit('ack', {'id': machine_id, 'status': 'updated'}, to=sid)
    else:
        print(f"⚠️ Unknown machine ID: {machine_id}")
        socketio.emit('ack', {'status': 'failed', 'reason': 'unknown id'}, to=sid)