# CSCE-500-Project — Mini Shop

Small FastAPI e-commerce app (video-game shop). Auth, products, cart, and orders. We chose **Option B — E-commerce**. Store managers create and edit products; customers search products, add them to a cart, and place orders. Data is stored in PostgreSQL (Supabase). The browser talks to an HTTP API (FastAPI); only the API talks to the database.

> **This is a CSCE 553 class baseline, not a production system. All users and data are fake.**

## Live URLs

- **Public app:** https://csce-500-project.onrender.com
- **Interactive API docs:** https://csce-500-project.onrender.com/docs
- **Repository:** https://github.com/chloemich04/CSCE-500-Project

> The app is hosted on Render's free tier and spins down after ~15 minutes of inactivity. The first request after idle can take about a minute (cold start).

## Architecture

```
Browser (HTML pages + JS)
      |  HTTPS
      v
FastAPI application  (JSON API + server-rendered HTML)   - hosted on Render
      |  DATABASE_URL (SQLAlchemy / psycopg2)
      v
PostgreSQL database  - hosted on Supabase

```

The browser stores the JWT returned at login and sends it on protected calls. The browser never talks to Supabase directly - only the Python API uses `DATABASE_URL`.

## Demo accounts

All three use the password: `ClassDemo123!`


| Email             | Password      | Account type |
| ----------------- | ------------- | ------------ |
| alex@example.com  | ClassDemo123! | customer     |
| blair@example.com | ClassDemo123! | customer     |
| casey@example.com | ClassDemo123! | customer     |


## Python virtual environment

Follow these steps to create and use a project-local Python virtual environment and manage dependencies.

**Create venv (Windows PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

```

**Create venv (Windows CMD):**

```bat
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

```

**Create venv (macOS / Linux):**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

```

**One-step setup scripts:** Use `setup_venv.bat` on Windows or `setup_venv.sh` on macOS/Linux to create the venv and install requirements.

**Add dependencies:** After installing packages during development, freeze them into requirements.txt:

```bash
python -m pip freeze > requirements.txt

```

Notes:

- The virtual environment is created in the repository root at `.venv` and is ignored by Git.
- Keep `requirements.txt` up to date so teammates can reproduce the environment.

## 1. Environment variables

- Copy `.env.example` to `.env` (`.env` is gitignored - do not commit it).
- Set `DATABASE_URL` to your Supabase Postgres connection URI (Project Settings -> Database). Use the **session pooler** URI (`...pooler.supabase.com...`) if you connect over an IPv4 network.
- Set `JWT_SECRET` to a long random string.
- Optional: `PORT` (default 8000), `JWT_EXPIRE_MINUTES` (default 60).

If the URI starts with `postgres://`, the app converts it to `postgresql://` automatically. If the connection fails, add `?sslmode=require` at the end of the URL.

In production (Render), set `DATABASE_URL` and `JWT_SECRET` as environment variables in the dashboard - never commit real values.

## 2. Create the database tables

In the Supabase dashboard, open SQL Editor, paste `schema.sql`, and run it. It creates `users`, `products`, and the cart/order tables (`carts`, `cart_items`, `orders`, `order_items`). The cart/order foreign keys require `products` to exist first, so run the file top to bottom.

## 3. Run the app

From the project root, with the venv activated:

```bash
python -m app.main

```

Or:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

```

The port comes from `PORT` in `.env` when you use `python -m app.main`. The server listens on `0.0.0.0`. Open http://127.0.0.1:8000 in a browser.

## 4. What you can test

### HTML pages


| Page            | URL                  | Purpose                                |
| --------------- | -------------------- | -------------------------------------- |
| Home            | GET /                | Landing page with auth status          |
| Register        | GET /register        | Create a new account                   |
| Login           | GET /login           | Log in with email/password             |
| Products        | GET /products        | Public product listing and search      |
| Manage Products | GET /products/manage | Store manager add/edit form            |
| Cart            | GET /cart            | View cart, change quantities, checkout |
| Orders          | GET /orders          | View past orders                       |


Logout is a button on the home page (clears the JWT stored in the browser).

### JSON API

Base URL (hosted): `https://csce-500-project.onrender.com`


| Method | Path                 | Auth   | Body                              | Success                              |
| ------ | -------------------- | ------ | --------------------------------- | ------------------------------------ |
| GET    | /health              | -      | -                                 | `{"status": "ok"}`                   |
| POST   | /api/auth/register   | -      | `{email, password, account_type}` | 201 + user JSON                      |
| POST   | /api/auth/login      | -      | `{email, password}`               | `{"access_token": "..."}`            |
| GET    | /api/products        | -      | -                                 | `[{id, name, price, stock, ...}]`    |
| GET    | /api/products/search | -      | `?q=<query>`                      | Matching products array              |
| POST   | /api/products        | Bearer | `{name, price, stock, ...}`       | 201 + product JSON (manager only)    |
| PUT    | /api/products/{id}   | Bearer | `{name, price, stock, ...}`       | 200 + updated product (manager only) |
| POST   | /api/cart            | Bearer | `{product_id, quantity}`          | 201 + cart JSON                      |
| GET    | /api/cart            | Bearer | -                                 | Cart with items + total              |
| PUT    | /api/cart/{item_id}  | Bearer | `{quantity}`                      | 200 + updated cart                   |
| DELETE | /api/cart/{item_id}  | Bearer | -                                 | 200 + updated cart                   |
| POST   | /api/orders          | Bearer | -                                 | 201 + order (checkout, empties cart) |
| GET    | /api/orders          | Bearer | -                                 | User's orders with items             |


**Auth notes:**

- `account_type` must be `"customer"` or `"store_manager"`.
- Passwords are hashed before storage (min. 8 characters); plain-text passwords are never stored.
- The login token is a JWT. Protected routes use `Authorization: Bearer <token>`.
- Only `store_manager` accounts can create/update products.
- Access control is intentionally light: `account_type` is stored on the user, without a hardened permission system.

## curl examples (against the hosted URL)

On Windows use `curl.exe`. Replace `TOKEN` with the `access_token` returned by login.

```bash
BASE=https://csce-500-project.onrender.com

# Health check (read)
curl -sS "$BASE/health"
# {"status":"ok"}

# Register
curl -sS -X POST "$BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"alex@example.com","password":"ClassDemo123!","account_type":"customer"}'

# Login (returns a JWT)
curl -sS -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"alex@example.com","password":"ClassDemo123!"}'

# List products (read)
curl -sS "$BASE/api/products"

# Search products (read)
curl -sS "$BASE/api/products/search?q=game"

# Add a product to the cart (write, requires token)
curl -sS -X POST "$BASE/api/cart" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"product_id":1,"quantity":2}'

# View the cart (read, requires token)
curl -sS "$BASE/api/cart" \
  -H "Authorization: Bearer TOKEN"

# Checkout: create an order from the cart (write, requires token)
curl -sS -X POST "$BASE/api/orders" \
  -H "Authorization: Bearer TOKEN"

# Create a product as a store_manager (write, requires manager token)
curl -sS -X POST "$BASE/api/products" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"name":"Game Title","price":29.99,"stock":10,"category":"games","platform":"PC"}'

```

## Project layout

```
app/                     FastAPI application
  main.py                Health, auth, product/cart/order pages + server entry
  config.py              Reads .env
  database.py            PostgreSQL via DATABASE_URL
  models.py              User, Product, Cart, Order table mappings
  schemas.py             Request/response JSON shapes
  auth.py                Password hash + JWT
  routers/
    auth.py              /api/auth/register and /login
    products.py          /api/products (CRUD + search)
    cart.py              /api/cart (add/view/update/remove)
    orders.py            /api/orders (checkout + list)
templates/               Jinja2 HTML pages
  base.html              Navigation and layout template
  index.html             Home page
  register.html          Registration form
  login.html             Login form
  products.html          Public product list and search
  product_manager.html   Store manager add/edit product form
  cart.html              Cart view + checkout
  orders.html            Order history
static/                  CSS + JavaScript
  styles.css             Styling for all pages
  auth.js                JWT management and auth UI state
schema.sql               SQL to run in Supabase (users + products + cart/orders)
.env.example             Placeholders only

```

## Notes

- "Buy" creates an order row in the database - there is no real payment processing.
- The browser never talks to Supabase directly. Only the Python API uses `DATABASE_URL`.
- **Not a production system. Fake data only.**

