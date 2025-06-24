@echo off
cd /d D:\ESP32\Machine200Server
waitress-serve --port=5001 --threads=50 --connection-limit=500 wsgi:app > waitress.log 2>&1