@echo off
setlocal

set "MOSQUITTO_SUB=%ProgramFiles%\mosquitto\mosquitto_sub.exe"
if not exist "%MOSQUITTO_SUB%" (
    where mosquitto_sub.exe >nul 2>&1
    if errorlevel 1 (
        echo Instala Eclipse Mosquitto para ejecutar esta prueba.
        exit /b 1
    )
    set "MOSQUITTO_SUB=mosquitto_sub.exe"
)

set "TOPICO=utp/ds8/1gs133/sls-smart-lighting/telemetria-francesco/telemetria"
echo Escuchando %TOPICO% en broker.emqx.io:1883
echo Inicia Wokwi. Debe llegar una muestra JSON cada 2 segundos.
echo Pulsa Ctrl+C para cerrar el suscriptor.
"%MOSQUITTO_SUB%" -h broker.emqx.io -p 1883 -t "%TOPICO%" -v -q 1 %*
exit /b %ERRORLEVEL%
