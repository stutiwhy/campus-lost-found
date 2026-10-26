@echo off
set "PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin"
setlocal

REM One-time migration: remove the container the old Jenkinsfile created by hand.
docker rm -f campus-lost-found >NUL 2>&1

docker compose -p campus-lost-found up -d --build --wait --wait-timeout 90
if errorlevel 1 (
    echo Deployment failed - last app logs:
    docker compose -p campus-lost-found logs --tail 50 app
    exit /b 1
)

docker compose -p campus-lost-found ps
docker image prune -f
exit /b 0
