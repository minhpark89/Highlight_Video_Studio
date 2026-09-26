@echo off
rem Wrapper bat khoi chay Watchdog an toan cho Highlight Video Studio (port 5080)
cd /d "D:\Highlight_Video_Studio"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "D:\Highlight_Video_Studio\watchdog_safe.ps1"
