@echo off
setlocal
pushd "%~dp0" || exit /b 1
python -u -m backend.main --broker broker.emqx.io --prefijo utp/ds8/1gs133/sls-smart-lighting --puerto 8017
set "RESULTADO=%ERRORLEVEL%"
popd
exit /b %RESULTADO%
