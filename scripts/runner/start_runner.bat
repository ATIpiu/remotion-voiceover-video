@echo off
rem Copy this file + runner.ps1 into <project>\scripts\ and double-click. Root = parent of scripts\
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0runner.ps1" -Root "%~dp0.."
pause
