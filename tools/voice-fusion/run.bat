@echo off
cd /d "%~dp0"
cls
set PYTHONUTF8=1
python -X utf8 run.py
exit
