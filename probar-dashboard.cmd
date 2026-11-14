@echo off
setlocal
pushd "%~dp0" || exit /b 1

python -c "import paho.mqtt.client" 2>nul
if errorlevel 1 (
    echo Instala las dependencias con: python -m pip install -r backend/requirements.txt
    popd
    exit /b 1
)

set "URL=http://127.0.0.1:8018/"
echo Dashboard: %URL%
start "" /min python -c "import time, webbrowser; time.sleep(2); webbrowser.open('%URL%')"
python -u -m backend.main --broker broker.emqx.io --prefijo utp/ds8/1gs133/sls-smart-lighting --puerto 8018
set "RESULTADO=%ERRORLEVEL%"
popd
exit /b %RESULTADO%
