@echo off
chcp 65001 >nul
setlocal
rem Abre el Estudio Virtual en http://localhost:8000
cd /d "%~dp0..\.."

where uv >nul 2>&1
if errorlevel 1 set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>&1
if errorlevel 1 (
  echo Falta uv. Primero haz doble clic en scripts\windows\instalar.bat
  pause
  exit /b 1
)

pushd backend
uv run python -m app.run
set "STATUS=%errorlevel%"
popd
if not "%STATUS%"=="0" (
  echo.
  echo La app se cerro con un error ^(codigo %STATUS%^).
  pause
)
exit /b %STATUS%
