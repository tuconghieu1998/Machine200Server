Open Cmd as Admin and Run
netsh advfirewall set allprofiles state off

install python

pip install flask
pip install pyodbc
pip install dotenv
pip install requests

pip install waitress

Run dev:
python app.py

Run deploy
waitress-serve --port=5001 wsgi:app > waitress.log 2>&1

Check log:
Get-Content waitress.log -Wait

2. Add to Task Scheduler
Open Task Scheduler (Win + R → type taskschd.msc → Enter).

Click Create Basic Task.

Name: Machine200Server

Trigger: Select "When the computer starts".

Action: Choose "Start a Program" → Browse → Select start_flask.bat.

Click Finish.


Docker:
-- Setup:
Install WSL, Docker Desktop

Open Powershell as Admin
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

Restart PC

Create Dockerfile, docker-compose.yaml, .dockerignore
-- Build & Run: 
docker-compose up --build
-- Build:
docker build -t machine200server:latest . 
