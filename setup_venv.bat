@echo off
REM Create a virtual environment in .venv, activate it, upgrade pip, and install requirements
python -m venv .venv
if exist .venv\Scripts\Activate.ps1 (
  REM PowerShell activation (for interactive use)
  echo Created virtual environment in .venv. To activate in PowerShell run:
  echo .\.venv\Scripts\Activate.ps1
) else (
  call .venv\Scripts\activate.bat
)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo Setup complete. Activate the environment before running Python commands.