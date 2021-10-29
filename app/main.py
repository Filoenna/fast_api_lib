from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.responses import HTMLResponse

from .internal import admin
from .routers import books, users
from .core import security

app = FastAPI()

templates = Jinja2Templates(directory="front/templates")
app.mount("/static", StaticFiles(directory="front/static"), name="static")


app.include_router(users.router)
app.include_router(books.router)
app.include_router(security.router)


app.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
    responses={418: {"description": "I'm a teapot"}},
)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
