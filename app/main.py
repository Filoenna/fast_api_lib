from fastapi import (
    FastAPI,
    Request,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.config import Config
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from authlib.integrations.starlette_client import OAuth

from typing import Optional, List

from .internal import admin
from .routers import books, users
from .core import security

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="!secret")

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

config = Config(".env")
oauth = OAuth(config)

CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"
oauth.register(
    name="google",
    server_metadata_url=CONF_URL,
    client_kwargs={"scope": "openid email profile"},
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get("user")

    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/login", tags=["authentication"])  # Tag it as "authentication" for our docs
async def login(request: Request):
    # Redirect Google OAuth back to our application
    redirect_uri = request.url_for("auth")

    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.route("/auth")
async def auth(request: Request):
    # Perform Google OAuth
    token = await oauth.google.authorize_access_token(request)
    user = await oauth.google.parse_id_token(request, token)

    # Save the user
    request.session["user"] = dict(user)

    return RedirectResponse(url="/")


@app.get("/logout", tags=["authentication"])  # Tag it as "authentication" for our docs
async def logout(request: Request):
    # Remove the user
    request.session.pop("user", None)

    return RedirectResponse(url="/")


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left the chat")
