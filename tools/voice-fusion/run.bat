@echo off
cd /d "%~dp0"
echo Watching for changes... (Ctrl+C to stop)
python -m watchfiles "python gui.py" --filter python .
