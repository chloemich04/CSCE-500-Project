# CSCE-500-Project — Mini Shop

Small FastAPI e-commerce app (baseline). This first slice includes **health**, **register**, **login**, and a **home page**. Products, cart, and orders will come after you test this.

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

## 1. Environment variables

1. Copy `.env.example` to `.env` (`.env` is gitignored — do not commit it).
2. Set `DATABASE_URL` to your **Supabase Postgres** connection URI (Project Settings → Database).
3. Set `JWT_SECRET` to a long random string.
4. Optional: `PORT` (default `8000`), `JWT_EXPIRE_MINUTES` (default `60`).

If the URI starts with `postgres://`, the app converts it to `postgresql://` automatically. If the connection fails, add `?sslmode=require` at the end of the URL.

## 2. Create the database table

In the Supabase dashboard, open **SQL Editor**, paste `schema.sql`, and run it. For this slice you only need the `users` table.

## 3. Run the app

From the project root, with the venv activated:

```powershell
python -m app.main
```

Or:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The port comes from `PORT` in `.env` when you use `python -m app.main`. The server listens on `0.0.0.0`.

Open http://127.0.0.1:8000 in a browser.

## 4. What you can test now

### HTML

| Page | URL |
|------|-----|
| Home | `GET /` |
| Register | `GET /register` |
| Login | `GET /login` |

Logout is a button on the home page (clears the JWT stored in the browser).

### JSON API

| Method | Path | Body | Success |
|--------|------|------|---------|
| `GET` | `/health` | — | `{"status": "ok"}` |
| `POST` | `/api/auth/register` | `{"email","password","account_type"}` | `201` + user JSON |
| `POST` | `/api/auth/login` | `{"email","password"}` | `{"access_token": "..."}` |

`account_type` must be `"customer"` or `"store_manager"`. Passwords are hashed with **passlib + bcrypt**. The login token is a **JWT**. Protected routes (next slice) will use `Authorization: Bearer <token>`.

Example (PowerShell):

```powershell
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/api/auth/register -H "Content-Type: application/json" -d "{\"email\":\"you@example.com\",\"password\":\"secret1\",\"account_type\":\"customer\"}"

curl -X POST http://127.0.0.1:8000/api/auth/login -H "Content-Type: application/json" -d "{\"email\":\"you@example.com\",\"password\":\"secret1\"}"
```

## Project layout

```
app/                 FastAPI application
  main.py            Health + HTML routes + server entry
  config.py          Reads .env
  database.py        PostgreSQL via DATABASE_URL
  models.py          User table mapping
  schemas.py         Request/response JSON shapes
  auth.py            Password hash + JWT
  routers/auth.py    /api/auth/register and /login
templates/           Jinja2 HTML pages
static/              CSS + small JS for the JWT in the browser
schema.sql           SQL to run in Supabase
.env.example         Placeholders only
```

The browser never talks to Supabase directly. Only the Python API uses `DATABASE_URL`.
