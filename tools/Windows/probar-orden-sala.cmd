@echo off
setlocal
set "PUB=%ProgramFiles%\mosquitto\mosquitto_pub.exe"
if not exist "%PUB%" (
    echo Instala Mosquitto para usar este lanzador.
    exit /b 1
)
set "TEMA=utp/ds8/1gs133/sls-smart-lighting/demo-sala-francesco/comandos"
echo Usa el firmware de esta rama en Wokwi con la configuracion incluida.
echo Inicia la simulacion y espera la conexion MQTT.
:menu
echo.
echo [1] Apagar Sala  [2] Probar orden invalida  [3] Volver a automatico  [4] Salir
choice /c 1234 /n /m "Selecciona una opcion: "
if errorlevel 4 exit /b 0
if errorlevel 3 (
    set "ACCION=auto"
) else if errorlevel 2 (
    set "ACCION=encender"
) else (
    set "ACCION=apagar"
)
echo {"id":"demo-%ACCION%","zona":"SALA","accion":"%ACCION%"}| "%PUB%" -h broker.emqx.io -p 1883 -t "%TEMA%" -q 1 -s
if errorlevel 1 (
    echo No se pudo publicar la orden.
) else (
    echo Orden enviada. Comprueba el resultado en la consola de Wokwi.
)
goto menu
