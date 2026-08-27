import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

app = FastAPI(title="CSCE 553 E-Commerce (skeleton)") # creating FastAPI instance

# Mounting the static files directory to serve static assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/health") # Health check endpoint to verify if the application is running
async def health_check():
    return {"status" : "ok"}

@app.get("/")   # Root endpoint to render the index.html template
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})