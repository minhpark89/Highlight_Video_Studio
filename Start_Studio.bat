@echo off
title Highlight Video Studio
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo       HIGHLIGHT VIDEO STUDIO - KHOI DONG
echo ========================================================
echo.

:: 1. Kiem tra Python tren he thong
set "PY="
where python >nul 2>nul
if %errorlevel% equ 0 set "PY=python"
if "%PY%"=="" (
    where py >nul 2>nul
    if %errorlevel% equ 0 set "PY=py"
)
if "%PY%"=="" (
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    if exist "C:\Python313\python.exe" set "PY=C:\Python313\python.exe"
    if exist "C:\Python312\python.exe" set "PY=C:\Python312\python.exe"
)

if "%PY%"=="" (
    echo [!] LOI: May tinh chua cai dat Python hoac chua them vao PATH!
    echo.
    echo Vui long cai Python tai: https://www.python.org/downloads/
    echo (Quan trong: Khi cai, nho tich chon "Add python.exe to PATH")
    echo.
    pause
    exit /b 1
)

echo [+] Da nhan dien Python: %PY%
echo [+] Thu muc goc: %~dp0
echo.

:: 2. Kiem tra thu vien chay web
echo [+] Kiem tra thu vien backend...
%PY% -c "import flask, waitress, requests, yt_dlp" >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Dang tu dong cai dat thu vien (Flask, Waitress, Requests)...
    %PY% -m pip install flask waitress requests yt-dlp
)

:: 3. Tu dong tao Shortcut ra Desktop neu chua co
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Highlight Video Studio.lnk'); $s.TargetPath = '%~dp0Start_Studio.bat'; $s.WorkingDirectory = '%~dp0'; $s.Save()" >nul 2>nul

:: 4. Mo trinh duyet sau 1.5 giay
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5080"

:: 5. Chay Server
echo.
echo ========================================================
echo   SERVER DANG CHAY TAI: http://localhost:5080
echo   (Giu nguyen cua so nay de he thong hoat dong)
echo ========================================================
echo.

%PY% run_server.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Co loi xay ra khien Server bi dung!
    pause
)
