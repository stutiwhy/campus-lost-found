@echo off
set "PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin"
setlocal
REM Smoke test the DEPLOYED container: call /health from inside it.
docker compose -p campus-lost-found exec -T app python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3).read().decode())"
exit /b %ERRORLEVEL%
