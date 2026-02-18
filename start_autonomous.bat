@echo off
echo Starting RTX Autonomous Mission...
cd C:\ClaudeAgent
start /B python autonomous\core_autonomy.py
echo RTX running 24/7. Check autonomous\progress.json for status.
echo To stop: create autonomous\STOP file
