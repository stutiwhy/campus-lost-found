@echo off
set "PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin"
setlocal
if "%BUILD_NUMBER%"=="" set BUILD_NUMBER=local
set COMPOSE=docker compose -f docker-compose.ci.yml -p lostfound-ci-%BUILD_NUMBER%

if not exist test-results mkdir test-results

%COMPOSE% up --build --abort-on-container-exit --exit-code-from tests
set RESULT=%ERRORLEVEL%

%COMPOSE% logs --no-color app > test-results\app.log 2>&1
%COMPOSE% down -v --remove-orphans

exit /b %RESULT%
