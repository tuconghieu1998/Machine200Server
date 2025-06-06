@echo off
cd /d C:\www\server\Machine200Server
waitress-serve --port=5001 wsgi:app > waitress.log 2>&1