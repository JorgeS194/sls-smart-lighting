@echo off
setlocal
set "SUB=%ProgramFiles%\mosquitto\mosquitto_sub.exe"
if not exist "%SUB%" (
    echo Instala Mosquitto para usar este lanzador.
    exit /b 1
)
set "TEMA=utp/ds8/1gs133/sls-smart-lighting/demo-sala-francesco/estado"
echo Inicia y detiene Wokwi para observar online y offline.
echo Retenido=1 indica un estado guardado por el broker.
echo Pulsa Ctrl+C para salir.
"%SUB%" -h broker.emqx.io -p 1883 -q 1 -t "%TEMA%" -F "retenido=%%r %%t %%p"
exit /b %ERRORLEVEL%
