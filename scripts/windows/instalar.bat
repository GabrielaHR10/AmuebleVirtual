@echo off
chcp 65001 >nul
setlocal
rem Instala todo lo necesario para el Estudio Virtual en Windows. Se puede correr varias veces.
cd /d "%~dp0..\.."

echo === Estudio Virtual - instalacion ===

where uv >nul 2>&1
if errorlevel 1 (
  echo Instalando uv ^(el instalador de Python^)...
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
where uv >nul 2>&1
if errorlevel 1 (
  echo ERROR: no se pudo instalar uv. Revisa tu conexion a internet y vuelve a intentar.
  pause
  exit /b 1
)

echo Instalando Python y librerias ^(la primera vez puede tardar varios minutos^)...
pushd backend
uv sync
if errorlevel 1 (
  popd
  echo ERROR: no se pudieron instalar las librerias. Revisa tu conexion a internet y vuelve a intentar.
  pause
  exit /b 1
)
popd

rem Precarga de modelos de IA: se agrega en la Fase 1 (uv run python -m app.prefetch)

echo.
echo Listo. Para abrir la app: doble clic en scripts\windows\iniciar.bat
if "%NO_PAUSE%"=="" pause
exit /b 0
