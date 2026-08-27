# CSCE-500-Project

## Python virtual environment

Follow these steps to create and use a project-local Python virtual environment and manage dependencies.

- **Create venv (Windows PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

- **Create venv (Windows CMD):**

```bat
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

- **Create venv (macOS / Linux):**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

- **One-step setup scripts:** Use `setup_venv.bat` on Windows or `setup_venv.sh` on macOS/Linux to create the venv and install requirements.

- **Add dependencies:** After installing packages during development, freeze them into `requirements.txt`:

```bash
python -m pip freeze > requirements.txt
```

- **Notes:**
	- The virtual environment is created in the repository root at `.venv` and is ignored by Git.
	- Keep `requirements.txt` up to date so teammates and CI can reproduce the environment.
