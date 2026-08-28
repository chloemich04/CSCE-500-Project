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

### Running the application

This project uses FastAPI with Uvicorn as the local development server.

### Windows PowerShell

Activate the virtual environment and start the server:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server listens on all network interfaces, but open the application in a browser using:

```text
http://127.0.0.1:8000/
```

Do not use `http://0.0.0.0:8000/` in the browser. `0.0.0.0` is only used as the server bind address.

## Current endpoints

- `GET /health` returns `{"status":"ok"}`.
- `POST /api/auth/register` creates an account.
- `POST /api/auth/login` verifies an account and returns a JWT bearer token.
- `GET /docs` opens FastAPI's interactive API documentation.

Example requests from PowerShell:

```powershell
$body = @{ email = "me@example.com"; password = "use-a-strong-password" } | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/register" `
    -Method POST -ContentType "application/json" -Body $body

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/login" `
    -Method POST -ContentType "application/json" -Body $body
```

Passwords are hashed with Argon2 and are never stored as plain text. The login response contains an access token that will be used for protected API routes as the project grows.

## Environment variables

Local configuration belongs in a `.env` file, which must not be committed to Git. Use placeholder values when sharing configuration with teammates:

```env
DATABASE_URL=your-supabase-postgresql-connection-string
DATABASE_NAME=your-database-name
DATABASE_PASSWORD=your-database-password
SECRET_KEY=your-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
PORT=8000
```

The application loads `.env` for local development. Render supplies the `PORT` environment variable in production, so the deployment configuration should use that value rather than hard-coding a production port.

## Current development limitation

Authentication is currently a learning scaffold. Registered users are stored in an in-memory dictionary, so accounts disappear whenever the server restarts. PostgreSQL persistence through Supabase still needs to be implemented before this is production-ready.
