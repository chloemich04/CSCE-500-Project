# CSCE-500-Project — Mini Shop

Small FastAPI e-commerce app (video-game shop). Auth, products, cart, and orders.

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

In the Supabase dashboard, open **SQL Editor**, paste `schema.sql`, and run it. The `products` table is owned by another teammate and must already exist before the cart/order foreign keys will succeed. If `users` already exists, run only the cart/order `CREATE TABLE` block.

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

| Page | URL | Purpose |
|------|-----|---------|
| Home | `GET /` | Landing page with auth status |
| Register | `GET /register` | Create a new account |
| Login | `GET /login` | Log in with email/password |
| Products | `GET /products` | Public product listing and search |
| Manage Products | `GET /products/manage` | Store manager add/edit form |
| Cart | `GET /cart` |
| Orders | `GET /orders` |

Logout is a button on the home page (clears the JWT stored in the browser).

### JSON API

| Method | Path | Auth | Body | Success |
|--------|------|------|------|---------|
| `GET` | `/health` | — | — | `{"status": "ok"}` |
| `POST` | `/api/auth/register` | — | `{"email","password","account_type"}` | `201` + user JSON |
| `POST` | `/api/auth/login` | — | `{"email","password"}` | `{"access_token": "..."}` |
| `GET` | `/api/products` | — | — | `[{id, name, price, stock, ...}]` |
| `GET` | `/api/products/search` | — | `?q=<query>` | Matching products array |
| `POST` | `/api/products` | Bearer | `{name, price, stock, ...}` | `201` + product JSON (manager only) |
| `PUT` | `/api/products/{id}` | Bearer | `{name, price, stock, ...}` | `200` + updated product (manager only) |

**Auth Notes:**
- `account_type` must be `"customer"` or `"store_manager"`.
- Passwords are hashed with **passlib + Argon2** (min. 8 characters).
- The login token is a **JWT**. Protected routes use `Authorization: Bearer <token>`.
- Only `store_manager` accounts can create/update products.

**Example (PowerShell):**

```powershell
# Health check
curl http://127.0.0.1:8000/health

# Register
curl -X POST http://127.0.0.1:8000/api/auth/register -H "Content-Type: application/json" -d "{\"email\":\"mgr@shop.com\",\"password\":\"SecurePass123\",\"account_type\":\"store_manager\"}"

# Login
curl -X POST http://127.0.0.1:8000/api/auth/login -H "Content-Type: application/json" -d "{\"email\":\"mgr@shop.com\",\"password\":\"SecurePass123\"}"

# List all products
curl http://127.0.0.1:8000/api/products

# Search products
curl "http://127.0.0.1:8000/api/products/search?q=game"

# Create a product (replace TOKEN with the access_token from login)
curl -X POST http://127.0.0.1:8000/api/products -H "Content-Type: application/json" -H "Authorization: Bearer TOKEN" -d "{\"name\":\"Game Title\",\"price\":29.99,\"stock\":10,\"category\":\"games\",\"platform\":\"PC\"}"

# Update a product (replace ID with product id and TOKEN with your access_token)
curl -X PUT http://127.0.0.1:8000/api/products/1 -H "Content-Type: application/json" -H "Authorization: Bearer TOKEN" -d "{\"name\":\"Game Title\",\"price\":24.99,\"stock\":5}"
```

## Project layout

```
app/                 FastAPI application
  main.py            Health, auth, product pages + server entry
  config.py          Reads .env
  database.py        PostgreSQL via DATABASE_URL
  models.py          User and Product table mappings
  schemas.py         Request/response JSON shapes (auth + products)
  auth.py            Password hash (Argon2) + JWT
  routers/
    auth.py          /api/auth/register and /login
    products.py      /api/products (CRUD + search)
templates/           Jinja2 HTML pages
  base.html          Navigation and layout template
  index.html         Home page
  register.html      Registration form
  login.html         Login form
  products.html      Public product list and search
  product_manager.html Store manager add/edit product form
static/              CSS + JavaScript
  styles.css         Styling for all pages
  auth.js            JWT management and auth UI state
schema.sql           SQL to run in Supabase (users + products)
.env.example         Placeholders only
```

The browser never talks to Supabase directly. Only the Python API uses `DATABASE_URL`.
