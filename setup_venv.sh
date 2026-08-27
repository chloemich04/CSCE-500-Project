#!/usr/bin/env bash
# Create a virtual environment in .venv, activate it, upgrade pip, and install requirements
set -e
python3 -m venv .venv
echo "Created virtual environment in .venv"
echo "To activate: source .venv/bin/activate"
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "Setup complete. Virtual environment is active."
