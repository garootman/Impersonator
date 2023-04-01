@echo off
cd /d %~dp0

if not exist venv (
  rem If it doesn't exist, create the virtual environment using 'python3 -m venv venv'
  python3 -m venv venv
)

call venv\Scripts\Activate.bat

pip install -r requirements.txt

python main.py

pause
