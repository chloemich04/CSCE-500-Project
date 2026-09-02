"""Mini Shop — FastAPI entry point (health, HTML pages, auth, and product API)."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import auth, products, cart, orders

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="Mini Shop")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/products", response_class=HTMLResponse)
def products_page(request: Request):
    return templates.TemplateResponse(request, "products.html")


@app.get("/products/manage", response_class=HTMLResponse)
def product_manager_page(request: Request):
    return templates.TemplateResponse(request, "product_manager.html")


@app.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request):
    return templates.TemplateResponse(request, "cart.html")


@app.get("/orders", response_class=HTMLResponse)
def orders_page(request: Request):
    return templates.TemplateResponse(request, "orders.html")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
