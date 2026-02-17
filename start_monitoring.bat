@echo off
REM Start GPU monitoring in background
REM Run this script to start 24/7 monitoring

echo Starting GPU Monitor for 24/7 operation...
cd /d C:\ClaudeAgent
set PYTHONIOENCODING=utf-8

start /B python gpu_monitor.py > monitor.out 2>&1

echo GPU Monitor started in background
echo Check logs: tail -f C:\ClaudeAgent\gpu_monitor.log
echo.
echo Press any key to exit...
pause
