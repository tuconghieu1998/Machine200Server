import pandas as pd

# Number of machines
num_entries = 200

# Prepare data list
data = []
for i in range(1, num_entries + 1):
    sensor_id = f"PZEM{i:04d}"
    machine_id = f"MC{i:03d}"
    mac = [0x02, (i >> 16) & 0xFF, (i >> 8) & 0xFF, i & 0xFF, 0x00, 0x01]
    mac_str = ':'.join(f"{b:02X}" for b in mac)
    data.append([sensor_id, mac_str, machine_id])

# Create DataFrame
df = pd.DataFrame(data, columns=["SensorID", "MAC Address", "MachineID"])

# Export to Excel
df.to_excel("Machine_MAC_List.xlsx", index=False)

print("Excel file 'Machine_MAC_List.xlsx' has been created.")
